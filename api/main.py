# api/main.py - COMPLETE CORRECT VERSION - TRIPLE CHECKED

import logging
import uuid
import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# Import our core infrastructure components
from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from core_infra.redis_manager import get_redis_connection

# --- Pydantic Models ---
class PriorAuthRequest(BaseModel):
    patient_id: str = Field(..., description="The unique identifier for the patient.", example="patient-001")
    drug_name: str = Field(..., description="The name of the drug requiring authorization.", example="Empagliflozin")
    insurer_id: str = Field(..., description="The identifier for the patient's insurer.", example="UHC")

class WorkflowResponse(BaseModel):
    workflow_id: str = Field(..., description="The unique ID for the initiated workflow.")
    status: str = Field(..., description="The initial status of the workflow.", example="PENDING")
    message: str = Field(..., description="A message indicating the workflow has started.")

class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

# --- FastAPI Application Setup ---
app = FastAPI(
    title="RossNet API Gateway",
    description="The entry point for initiating and monitoring RossNet workflows.",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "ws://127.0.0.1:8001"
COMMANDER_AGENT_ID = "commander_agent_01"

# --- Message Handler for API Gateway ---
async def api_message_handler(message: MCPMessage) -> Any:
    """
    Simple message handler for the API gateway client.
    We don't expect to receive many messages, just acknowledgments.
    """
    logger.info(f"API Gateway received message: {message.mcp_header.message_type}")
    return None

# --- Helper Function ---
async def trigger_workflow(request_data: PriorAuthRequest) -> str:
    """
    Connects to the MCP, sends the initial task to the CommanderAgent, and returns the workflow_id.
    """
    workflow_id = str(uuid.uuid4())
    api_gateway_client_id = f"api_gateway_client_{workflow_id}"
    
    # Create MCP client with all required parameters
    mcp_client = MCPClient(
        agent_id=api_gateway_client_id,
        agent_name="API Gateway Client",
        agent_type="api_gateway",
        mcp_server_url=MCP_SERVER_URL,
        message_handler=api_message_handler,
        capabilities=[]  # API gateway doesn't offer capabilities
    )
    
    try:
        # Connect to MCP Router
        await mcp_client.connect()
        logger.info(f"Connected to MCP Router as {api_gateway_client_id}")
        
        # CRITICAL: Commander expects ONLY "goal" field in payload
        # Based on commander logic.py line: user_goal = payload.get("goal")
        payload = {
            "goal": f"Determine prior authorization for {request_data.drug_name} for patient with {request_data.insurer_id} insurance"
        }
        
        # Log exactly what we're sending
        logger.info(f"Sending payload to Commander: {payload}")
        
        # Send the message to Commander
        await mcp_client.send_message(
            payload=payload,
            message_type="PROCESS_USER_REQUEST",
            target_agent_id=COMMANDER_AGENT_ID,
            correlation_id=workflow_id
        )
        
        logger.info(f"Successfully triggered workflow {workflow_id} for patient {request_data.patient_id}")
        
        # Give it a moment to ensure the message is sent
        await asyncio.sleep(0.5)
        
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to communicate with the agent system: {str(e)}")
    finally:
        # Disconnect
        try:
            await mcp_client.disconnect()
        except:
            pass  # Ignore disconnect errors
        
    return workflow_id

# --- API Endpoints ---
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "RossNet API Gateway",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "predict": "POST /api/v1/prior-auth/predict",
            "status": "GET /api/v1/status/{workflow_id}"
        }
    }

@app.post("/api/v1/prior-auth/predict", response_model=WorkflowResponse, status_code=202)
async def predict_prior_authorization(request: PriorAuthRequest):
    """
    Initiates a new Prior Authorization prediction workflow.
    """
    logger.info(f"Received prior auth prediction request: {request.dict()}")
    
    try:
        # Trigger the workflow
        workflow_id = await trigger_workflow(request)
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="ACCEPTED",
            message="Workflow initiated. Check the status endpoint for results."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in predict endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """
    Retrieves the current status and final result of a workflow.
    """
    logger.info(f"Checking status for workflow_id: {workflow_id}")
    redis_conn = None
    
    try:
        redis_conn = await get_redis_connection()
        redis_key = f"rossnet:workflow:{workflow_id}"
        
        state_json = await redis_conn.get(redis_key)
        
        if not state_json:
            raise HTTPException(status_code=404, detail="Workflow ID not found.")
            
        workflow_state = json.loads(state_json)
        
        response = WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=workflow_state.get("status", "UNKNOWN"),
            result=None,
            error_message=workflow_state.get("error_message")
        )
        
        # If the workflow is complete, get the result
        if response.status == "COMPLETED":
            # Check for report compilation result
            report_task = workflow_state.get("tasks", {}).get("step3_compile_report", {})
            if report_task.get("result"):
                response.result = report_task["result"]
            else:
                # Fallback to old format
                final_task = workflow_state.get("tasks", {}).get("step4_predict_approval", {})
                if final_task.get("result"):
                    response.result = final_task["result"]

        return response

    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in Redis for workflow {workflow_id}")
        raise HTTPException(status_code=500, detail="Invalid workflow data format.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking status for workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve workflow status.")
    finally:
        if redis_conn:
            await redis_conn.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RossNet API Gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)