# C:\Users\rossd\Downloads\RossNetAgents\scripts\analyze_memory_planner_test.py
# Version: 4.0-ADVANCED - Enhanced log correlation and workflow tracking
# Comprehensive Memory-Augmented Planner Test Analysis

import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

try:
    from core_infra.memory_manager import MemoryManager
    import chromadb
    import asyncio
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)


@dataclass
class LogCandidate:
    """Represents a candidate log file with scoring information"""

    path: Path
    score: float = 0.0
    drug_found: bool = False
    workflow_found: bool = False
    entities_match: bool = False
    time_proximity: float = 0.0
    modification_time: float = 0.0
    content_preview: str = ""


class MemoryPlannerAnalyzer:
    """Analyzes Memory-Augmented Planner performance and strategy effectiveness"""

    def __init__(self):
        # Fix log paths - check multiple possible locations INCLUDING PROJECT ROOT
        self.project_root = Path(project_root)

        # Check for logs in multiple locations
        possible_log_dirs = [
            self.project_root,  # Check project root directly (where your logs are)
            self.project_root / "logs",  # Project root logs subdirectory
            self.project_root / "RossNetAgents" / "logs",  # Alternative structure
            Path.cwd(),  # Current working directory
            Path.cwd() / "logs",  # Current working directory logs subdirectory
        ]

        self.logs_dir = None
        log_files_found = []

        # Look for directory with most log files
        for log_dir in possible_log_dirs:
            if log_dir.exists() and log_dir.is_dir():
                # Count log files in this directory
                log_count = len(list(log_dir.glob("*_agent_*.log")))
                if log_count > 0:
                    log_files_found.append((log_dir, log_count))
                    print(f"[INFO] Found {log_count} agent log files in: {log_dir}")

        # Use directory with most log files
        if log_files_found:
            log_files_found.sort(key=lambda x: x[1], reverse=True)
            self.logs_dir = log_files_found[0][0]
            print(f"[INFO] Using logs directory with most logs ({log_files_found[0][1]} files): {self.logs_dir}")
        else:
            # Default to project root if no logs found anywhere
            self.logs_dir = self.project_root
            print(f"[WARNING] No log files found in any location, defaulting to: {self.logs_dir}")

        # Reports directory
        self.reports_dir = self.project_root / "generated_reports"
        if not self.reports_dir.exists():
            self.reports_dir = self.project_root / "reports"  # Alternative name
            if not self.reports_dir.exists():
                # Check project root for PDFs
                self.reports_dir = self.project_root

        self.memory_manager = None
        self.analysis_results = {
            "planner_performance": {},
            "memory_utilization": {},
            "workflow_efficiency": {},
            "strategy_effectiveness": {},
            "recommendations": [],
            "log_analysis_metadata": {},
        }

        # Cache for workflow correlations
        self._workflow_cache = {}
        self._pdf_timestamps = {}

    async def initialize_memory(self):
        """Initialize memory manager for analysis"""
        try:
            self.memory_manager = MemoryManager()
            doc_count = self.memory_manager.collection.count()
            print(f"[OK] Connected to ChromaDB: {doc_count} documents")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to memory: {e}")
            return False

    def _find_pdf_for_drug(self, drug_name: str) -> Optional[Tuple[Path, float]]:
        """Find PDF file for the drug and return its path and timestamp"""
        if drug_name in self._pdf_timestamps:
            return self._pdf_timestamps[drug_name]

        pdf_patterns = [
            f"*{drug_name}*.pdf",
            f"*{drug_name.lower()}*.pdf",
            f"*{drug_name.upper()}*.pdf",
        ]

        pdf_files = []
        for pattern in pdf_patterns:
            pdf_files.extend(list(self.reports_dir.glob(pattern)))

        if pdf_files:
            # Get the most recent PDF
            latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
            timestamp = latest_pdf.stat().st_mtime
            self._pdf_timestamps[drug_name] = (latest_pdf, timestamp)
            return latest_pdf, timestamp

        return None

    def _score_log_candidate(
        self,
        candidate: LogCandidate,
        drug_name: str = None,
        workflow_id: str = None,
        reference_time: float = None,
    ) -> float:
        """Score a log candidate based on multiple factors"""
        score = 0.0

        # Drug name match (highest priority)
        if drug_name and candidate.drug_found:
            score += 40.0

            # Extra points if drug appears in filename
            if drug_name.lower() in candidate.path.name.lower():
                score += 10.0

        # Workflow ID match (high priority)
        if workflow_id and candidate.workflow_found:
            score += 30.0

        # Entity extraction match
        if candidate.entities_match:
            score += 20.0

        # Time proximity to reference (e.g., PDF creation time)
        if reference_time and candidate.modification_time:
            # Calculate time difference in minutes
            time_diff = abs(reference_time - candidate.modification_time) / 60.0

            # Score based on proximity (max 10 points for same minute, decreasing)
            if time_diff < 1:
                score += 10.0
            elif time_diff < 5:
                score += 8.0
            elif time_diff < 15:
                score += 5.0
            elif time_diff < 30:
                score += 3.0
            elif time_diff < 60:
                score += 1.0

        # Prefer newer files slightly
        age_hours = (datetime.now().timestamp() - candidate.modification_time) / 3600
        if age_hours < 1:
            score += 2.0
        elif age_hours < 24:
            score += 1.0

        candidate.score = score
        return score

    def _analyze_log_content(
        self,
        log_path: Path,
        drug_name: str = None,
        workflow_id: str = None,
        check_depth: int = 50000,
    ) -> LogCandidate:
        """Analyze log content and create a scored candidate"""
        candidate = LogCandidate(path=log_path, modification_time=log_path.stat().st_mtime)

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                # Read limited content for analysis
                content = f.read(check_depth)
                candidate.content_preview = content[:500]

                # Check for drug name
                if drug_name:
                    candidate.drug_found = drug_name.lower() in content.lower()

                    # Look for entity extraction with this drug
                    entity_patterns = [
                        rf"primary_drug['\"]:\s*['\"]({drug_name})['\"]",
                        rf"drug_name['\"]:\s*['\"]({drug_name})['\"]",
                        rf"Entities extracted:.*Drug=({drug_name})",
                    ]

                    for pattern in entity_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            candidate.entities_match = True
                            break

                # Check for workflow ID
                if workflow_id:
                    candidate.workflow_found = workflow_id in content

        except Exception as e:
            print(f"[WARNING] Error reading {log_path}: {e}")

        return candidate

    def _find_best_log_file(
        self,
        agent_type: str,
        drug_name: str = None,
        workflow_id: str = None,
        specific_log_path: str = None,
        time_window_minutes: int = 60,
    ) -> Optional[Path]:
        """Find the most appropriate log file for analysis with advanced scoring"""

        # If specific log path provided, use it
        if specific_log_path:
            log_path = Path(specific_log_path)
            if log_path.exists():
                print(f"[INFO] Using specified log file: {log_path}")
                return log_path
            else:
                # Try in logs directory
                log_path = self.logs_dir / specific_log_path
                if log_path.exists():
                    print(f"[INFO] Using specified log file: {log_path}")
                    return log_path
                print(f"[WARNING] Specified log file not found: {specific_log_path}")

        # Get reference time from PDF if available
        reference_time = None
        if drug_name:
            pdf_info = self._find_pdf_for_drug(drug_name)
            if pdf_info:
                pdf_path, pdf_time = pdf_info
                reference_time = pdf_time
                print(
                    f"[INFO] Using PDF timestamp as reference: {datetime.fromtimestamp(pdf_time).strftime('%Y-%m-%d %H:%M:%S')}"
                )

        # Build patterns based on drug name
        patterns = []
        if drug_name:
            # Drug-specific patterns (most specific first)
            drug_lower = drug_name.lower()
            drug_abbrev = drug_name[:4].lower()  # e.g., "sota" for Sotagliflozin
            drug_upper = drug_name.upper()

            patterns.extend(
                [
                    f"{agent_type}_{drug_name}_*.log",
                    f"{agent_type}_{drug_lower}_*.log",
                    f"{agent_type}_{drug_upper}_*.log",
                    f"{agent_type}*{drug_name}*.log",
                    f"{agent_type}*{drug_lower}*.log",
                    f"{agent_type}_{drug_abbrev}_*.log",
                    f"{agent_type}*{drug_abbrev}*.log",
                ]
            )

        # Add workflow-specific patterns if available
        if workflow_id:
            patterns.extend(
                [
                    f"{agent_type}*{workflow_id[:8]}*.log",
                    f"{agent_type}*{workflow_id}*.log",
                ]
            )

        # Generic patterns (fallback)
        patterns.extend(
            [
                f"{agent_type}_*.log",
                f"{agent_type}*.log",
                f"*{agent_type}*.log",
            ]
        )

        # Collect all matching files
        all_matches = set()
        for pattern in patterns:
            matches = self.logs_dir.glob(pattern)
            all_matches.update(matches)

        if not all_matches:
            print(f"[WARNING] No {agent_type} logs found in {self.logs_dir}")
            return None

        # Analyze and score each candidate
        candidates = []
        print(f"[INFO] Analyzing {len(all_matches)} {agent_type} log candidates...")

        for log_file in all_matches:
            # Skip if file is too old (beyond time window)
            if reference_time and time_window_minutes > 0:
                age_minutes = (datetime.now().timestamp() - log_file.stat().st_mtime) / 60
                if age_minutes > time_window_minutes * 2:  # Be generous with the window
                    continue

            candidate = self._analyze_log_content(log_file, drug_name, workflow_id)
            self._score_log_candidate(candidate, drug_name, workflow_id, reference_time)

            if candidate.score > 0:
                candidates.append(candidate)

        if not candidates:
            # If no scored candidates, just return the most recent file
            latest = max(all_matches, key=lambda p: p.stat().st_mtime)
            print(f"[WARNING] No high-scoring candidates found, using most recent: {latest.name}")
            return latest

        # Sort by score and show top candidates
        candidates.sort(key=lambda c: c.score, reverse=True)

        print(f"\n[INFO] Top {min(3, len(candidates))} candidates for {agent_type}:")
        for i, candidate in enumerate(candidates[:3]):
            print(f"  {i + 1}. {candidate.path.name} (score: {candidate.score:.1f})")
            print(f"     - Drug found: {candidate.drug_found}, Workflow found: {candidate.workflow_found}")
            print(f"     - Entities match: {candidate.entities_match}")
            print(
                f"     - Modified: {datetime.fromtimestamp(candidate.modification_time).strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Return the highest scoring candidate
        selected = candidates[0]
        print(f"\n[INFO] Selected: {selected.path.name} (score: {selected.score:.1f})")

        # Store selection metadata
        self.analysis_results["log_analysis_metadata"][agent_type] = {
            "selected_log": str(selected.path.name),
            "score": selected.score,
            "drug_found": selected.drug_found,
            "workflow_found": selected.workflow_found,
            "entities_match": selected.entities_match,
            "candidates_analyzed": len(candidates),
        }

        return selected.path

    def analyze_planner_logs(
        self,
        workflow_id: str = None,
        drug_name: str = None,
        planner_log_path: str = None,
    ) -> Dict[str, Any]:
        """Analyze planner logs for memory-augmented behavior"""
        print("\n=== ANALYZING PLANNER LOGS ===")
        print(f"Target drug: {drug_name}")
        print(f"Target workflow: {workflow_id or 'Not specified'}")

        # Find the best planner log file
        planner_log = self._find_best_log_file("planner_agent", drug_name, workflow_id, planner_log_path)

        if not planner_log:
            print(f"[ERROR] No suitable planner log found for drug='{drug_name}', workflow='{workflow_id}'")
            print(f"[INFO] Searched in: {self.logs_dir}")
            return {}

        print(f"\nAnalyzing: {planner_log.name}")
        print(f"Log size: {planner_log.stat().st_size:,} bytes")
        print(f"Log modified: {datetime.fromtimestamp(planner_log.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")

        analysis = {
            "memory_queries": [],
            "strategy_determined": None,
            "entities_extracted": {},
            "plan_generation_time": None,
            "memory_insights_used": False,
            "gpt4_called": False,
            "fallback_used": False,
            "log_file": str(planner_log.name),
            "enhanced_features_used": False,
            "correct_drug_found": False,
            "workflow_id_found": False,
        }

        try:
            with open(planner_log, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

                # Verify this log contains the drug we're looking for
                if drug_name:
                    drug_occurrences = len(re.findall(rf"\b{drug_name}\b", content, re.IGNORECASE))
                    if drug_occurrences > 0:
                        analysis["correct_drug_found"] = True
                        print(f"[OK] Confirmed: Drug '{drug_name}' found {drug_occurrences} times in log")
                    else:
                        print(f"[WARNING] Drug '{drug_name}' not found in log content")

                # Look for workflow ID if provided
                if workflow_id:
                    if workflow_id in content:
                        analysis["workflow_id_found"] = True
                        print(f"[OK] Workflow ID {workflow_id} found in log")
                    else:
                        print(f"[WARNING] Workflow ID {workflow_id} not found in log")

                # Check for enhanced memory features
                if "EnhancedMemoryManager V2.0" in content:
                    analysis["enhanced_features_used"] = True
                    print("[OK] Enhanced Memory Manager V2.0 detected")

                # Extract entities - look for multiple patterns
                entity_patterns = [
                    r"Enhanced entity extraction completed: ({.*?})",
                    r"Extracted entities: ({.*?})",
                    r"Entity extraction result: ({.*?})",
                    r"entities_extracted['\"]:\s*({.*?})",
                ]

                entity_found = False
                for pattern in entity_patterns:
                    # Search for ALL occurrences to find the right one
                    matches = list(re.finditer(pattern, content, re.DOTALL))

                    for match in matches:
                        try:
                            # Clean up the match
                            entities_str = match.group(1)
                            # Replace single quotes with double quotes for valid JSON
                            entities_str = entities_str.replace("'", '"')
                            # Handle None values
                            entities_str = entities_str.replace("None", "null")

                            # Try to parse
                            extracted_entities = json.loads(entities_str)
                            extracted_drug = extracted_entities.get("primary_drug") or extracted_entities.get(
                                "drug_name"
                            )
                            extracted_disease = extracted_entities.get("primary_disease") or extracted_entities.get(
                                "disease_name"
                            )

                            # Check if this extraction matches our target drug
                            if drug_name and extracted_drug:
                                if extracted_drug.lower() == drug_name.lower():
                                    analysis["entities_extracted"] = extracted_entities
                                    print(
                                        f"[OK] Found matching entity extraction: Drug={extracted_drug}, Disease={extracted_disease}"
                                    )
                                    entity_found = True
                                    break
                                else:
                                    print(
                                        f"[INFO] Found entity extraction for different drug: {extracted_drug} (looking for {drug_name})"
                                    )
                            elif not drug_name:
                                # If no specific drug specified, take the first valid extraction
                                analysis["entities_extracted"] = extracted_entities
                                print(f"[OK] Entities extracted: Drug={extracted_drug}, Disease={extracted_disease}")
                                entity_found = True
                                break

                        except Exception:
                            # Try eval as fallback
                            try:
                                extracted_entities = eval(match.group(1))
                                extracted_drug = extracted_entities.get("primary_drug") or extracted_entities.get(
                                    "drug_name"
                                )

                                if drug_name and extracted_drug and extracted_drug.lower() == drug_name.lower():
                                    analysis["entities_extracted"] = extracted_entities
                                    print(f"[OK] Found matching entity extraction (via eval): {extracted_entities}")
                                    entity_found = True
                                    break
                            except:
                                pass

                    if entity_found:
                        break

                # Warn if we couldn't find matching entities
                if not entity_found and drug_name:
                    print(f"[WARNING] Could not find entity extraction for {drug_name} in this log")

                # Check memory insights gathering
                memory_insight_patterns = [
                    "Retrieving enhanced memory insights",
                    "Retrieving synchronous memory insights",
                    "Gathering memory insights for intelligent planning",
                    "memory insights gathered",
                ]

                for pattern in memory_insight_patterns:
                    if pattern in content:
                        analysis["memory_insights_used"] = True
                        print("[OK] Memory insights gathered")
                        break

                # Extract strategy - look for the most recent occurrence
                strategy_patterns = [
                    r"Enhanced memory insights completed: (\w+) strategy recommended",
                    r"Synchronous enhanced insights: (\w+) strategy",
                    r"Memory insights gathered: (\w+) strategy recommended",
                    r"Synchronous memory insights: (\w+) strategy recommended",
                    r"strategy recommended: (\w+)",
                    r"Using (\w+) strategy",
                    r"research_strategy['\"]:\s*['\"](\w+)['\"]",
                ]

                # Find all strategy mentions and use the most recent one
                all_strategies = []
                for pattern in strategy_patterns:
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    for match in matches:
                        strategy = match.group(1).lower()
                        position = match.start()
                        all_strategies.append((position, strategy))

                if all_strategies:
                    # Sort by position and take the last one
                    all_strategies.sort(key=lambda x: x[0])

                    # If drug_name specified, try to find strategy near drug mention
                    if drug_name and len(all_strategies) > 1:
                        # Find drug mentions
                        drug_positions = [m.start() for m in re.finditer(rf"\b{drug_name}\b", content, re.IGNORECASE)]

                        if drug_positions:
                            # Find strategy closest to a drug mention
                            best_strategy = None
                            min_distance = float("inf")

                            for strat_pos, strategy in all_strategies:
                                for drug_pos in drug_positions:
                                    distance = abs(strat_pos - drug_pos)
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_strategy = strategy

                            if best_strategy:
                                analysis["strategy_determined"] = best_strategy
                                print(f"[OK] Strategy determined (near {drug_name} mention): {best_strategy}")

                    # If no strategy found near drug mention, use the last one
                    if not analysis["strategy_determined"]:
                        analysis["strategy_determined"] = all_strategies[-1][1]
                        print(f"[OK] Strategy determined (most recent): {analysis['strategy_determined']}")

                # Check GPT-4 usage
                gpt4_patterns = [
                    "Sending enhanced memory-augmented prompt to GPT-4",
                    "Sending memory-augmented prompt to GPT-4",
                    "Calling GPT-4 with",
                    "OpenAI API call",
                ]

                for pattern in gpt4_patterns:
                    if pattern in content:
                        analysis["gpt4_called"] = True
                        print("[OK] GPT-4 called with memory-augmented prompt")
                        break

                # Extract timing if available
                time_patterns = [
                    r"Received GPT-4 response.*?(\d+\.\d+)s",
                    r"LLM response received in (\d+\.\d+)s",
                    r"Plan generation took (\d+\.\d+)s",
                    r"Enhanced plan created in (\d+\.\d+)s",
                ]

                for pattern in time_patterns:
                    time_match = re.search(pattern, content)
                    if time_match:
                        analysis["plan_generation_time"] = float(time_match.group(1))
                        print(f"[OK] Plan generation time: {analysis['plan_generation_time']}s")
                        break

                # Check for fallback
                fallback_patterns = [
                    "Fallback plan created",
                    "Using fallback plan",
                    "Enhanced fallback plan created",
                    "OpenAI client not available",
                ]

                for pattern in fallback_patterns:
                    if pattern in content:
                        analysis["fallback_used"] = True
                        print("[WARNING] Fallback plan was used")
                        break

                # Extract final plan structure - look for the most complete one
                plan_patterns = [
                    r"FINAL ENHANCED PLAN.*?({.*?})\s*$",
                    r"ENHANCED FALLBACK PLAN.*?({.*?})\s*$",
                    r"FINAL PLAN TO BE SENT BY PLANNER: ({.*?})",
                    r"Generated plan: ({.*?})",
                    r"Plan created: ({.*?})",
                ]

                plan_found = False
                for pattern in plan_patterns:
                    plan_matches = list(re.finditer(pattern, content, re.DOTALL | re.MULTILINE))

                    for plan_match in reversed(plan_matches):  # Start from the end
                        try:
                            plan_json = plan_match.group(1)
                            # Clean up the JSON string
                            plan_json = re.sub(r"\n\s*", " ", plan_json)
                            plan_json = re.sub(r",\s*}", "}", plan_json)  # Remove trailing commas
                            plan_json = re.sub(r",\s*]", "]", plan_json)

                            plan = json.loads(plan_json)

                            # Verify this plan is for our drug if specified
                            plan_drug = plan.get("extracted_drug_name")
                            if drug_name and plan_drug:
                                if plan_drug.lower() != drug_name.lower():
                                    print(
                                        f"[INFO] Found plan for different drug: {plan_drug} (looking for {drug_name})"
                                    )
                                    continue

                            analysis["plan_structure"] = {
                                "memory_augmented": plan.get("memory_augmented", False),
                                "research_strategy": plan.get("research_strategy", "unknown"),
                                "steps_count": len(plan.get("steps", [])),
                                "workflow_goal": plan.get("workflow_goal", "")[:100] + "...",
                                "enhanced_features": plan.get("enhanced_features", {}),
                                "extracted_drug_name": plan.get("extracted_drug_name"),
                                "extracted_disease_name": plan.get("extracted_disease_name"),
                            }
                            print(
                                f"[OK] Plan structure analyzed: {analysis['plan_structure']['steps_count']} steps, strategy={analysis['plan_structure']['research_strategy']}"
                            )
                            plan_found = True
                            break

                        except Exception as e:
                            print(f"[DEBUG] Could not parse plan JSON: {e}")

                    if plan_found:
                        break

        except Exception as e:
            print(f"[ERROR] Error reading planner log: {e}")
            import traceback

            traceback.print_exc()

        # Final validation
        if drug_name and analysis.get("entities_extracted"):
            extracted_drug = analysis["entities_extracted"].get("primary_drug") or analysis["entities_extracted"].get(
                "drug_name"
            )
            if extracted_drug and extracted_drug.lower() != drug_name.lower():
                print("\n[CRITICAL WARNING] Drug mismatch detected!")
                print(f"  - Expected: {drug_name}")
                print(f"  - Found: {extracted_drug}")
                print("  - This log may be from a different workflow!")

        self.analysis_results["planner_performance"] = analysis
        return analysis

    def analyze_workflow_execution(
        self,
        workflow_id: str = None,
        drug_name: str = None,
        router_log_path: str = None,
        commander_log_path: str = None,
    ) -> Dict[str, Any]:
        """Analyze complete workflow execution efficiency"""
        print("\n=== ANALYZING WORKFLOW EXECUTION ===")

        analysis = {
            "workflow_completed": False,
            "total_duration": None,
            "steps_executed": [],
            "api_calls_made": {"pubmed": 0, "clinical_trials": 0, "fda": 0},
            "data_retrieved": {
                "pubmed_articles": 0,
                "clinical_trials": 0,
                "adverse_events": 0,
            },
            "pdf_generated": False,
            "memory_stored": False,
        }

        # Check RouterAgent logs
        router_log = self._find_best_log_file("router_agent", drug_name, workflow_id, router_log_path)

        if router_log:
            try:
                with open(router_log, "r", encoding="utf-8", errors="ignore") as f:
                    router_content = f.read()

                    # Check workflow completion
                    completion_patterns = [
                        r"WORKFLOW_COMPLETE",
                        r"workflow.*completed successfully",
                        r"All steps completed",
                        r"Workflow.*COMPLETED",
                    ]

                    for pattern in completion_patterns:
                        if re.search(pattern, router_content, re.IGNORECASE):
                            analysis["workflow_completed"] = True
                            print("[OK] Workflow completed successfully")
                            break

                    # Extract executed steps
                    step_patterns = [
                        r"Executing step[:\s]+(\w+)",
                        r"Processing step[:\s]+(\w+)",
                        r"Running step[:\s]+(\w+)",
                        r"Step (\w+) completed",
                        r"Completed step[:\s]+(\w+)",
                    ]

                    executed_steps = set()
                    for pattern in step_patterns:
                        step_matches = re.findall(pattern, router_content, re.IGNORECASE)
                        executed_steps.update(step_matches)

                    if executed_steps:
                        analysis["steps_executed"] = list(executed_steps)
                        print(f"[OK] Steps executed: {', '.join(analysis['steps_executed'])}")
            except Exception as e:
                print(f"[ERROR] Error reading router log: {e}")

        # Check worker agent logs for data retrieval
        worker_configs = [
            (
                "pubmed_search_agent",
                "web_research_agent",
                [
                    r"Retrieved (\d+) articles",
                    r"Found (\d+) articles",
                    r"articles found: (\d+)",
                    r"Total articles: (\d+)",
                    r"Retrieved (\d+) PubMed articles",
                    r"Successfully retrieved (\d+) articles",
                ],
                "pubmed_articles",
                "pubmed",
            ),
        ]

        for primary_name, alt_name, patterns, data_key, api_key in worker_configs:
            worker_log = self._find_best_log_file(primary_name, drug_name, workflow_id) or self._find_best_log_file(
                alt_name, drug_name, workflow_id
            )

            if worker_log:
                try:
                    with open(worker_log, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        for pattern in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                # Use the last match (most recent)
                                count = int(matches[-1])
                                if count > 0:  # Only count if we actually got data
                                    analysis["data_retrieved"][data_key] = count
                                    analysis["api_calls_made"][api_key] = 1
                                    print(f"[OK] {data_key}: {count}")
                                    break
                except Exception as e:
                    print(f"[ERROR] Error reading {primary_name} log: {e}")

        # Check for PDF generation
        pdf_info = self._find_pdf_for_drug(drug_name) if drug_name else None
        if pdf_info:
            pdf_path, pdf_time = pdf_info
            analysis["pdf_generated"] = True
            print(f"[OK] PDF generated: {pdf_path.name}")
            print(f"     Created: {datetime.fromtimestamp(pdf_time).strftime('%Y-%m-%d %H:%M:%S')}")

        # Check CommanderAgent for memory storage
        commander_log = self._find_best_log_file("commander_agent", drug_name, workflow_id, commander_log_path)

        if commander_log:
            try:
                with open(commander_log, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                    storage_patterns = [
                        r"Successfully stored workflow.*outputs",
                        r"Storing workflow outputs in memory",
                        r"store_workflow_outputs.*completed",
                        r"Enhanced storage completed",
                        r"Standard memory storage completed",
                        r"stored.*documents? in memory",
                    ]

                    for pattern in storage_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            analysis["memory_stored"] = True
                            print("[OK] Workflow outputs stored in memory")
                            break
            except Exception as e:
                print(f"[ERROR] Error reading commander log: {e}")

        self.analysis_results["workflow_efficiency"] = analysis
        return analysis

    async def analyze_memory_impact(self, drug_name: str) -> Dict[str, Any]:
        """Analyze how memory was impacted by the workflow"""
        print(f"\n=== ANALYZING MEMORY IMPACT FOR {drug_name} ===")

        if not self.memory_manager:
            print("[ERROR] Memory manager not initialized")
            return {}

        analysis = {
            "new_documents": 0,
            "updated_documents": 0,
            "cross_drug_evidence": [],
            "quality_distribution": {},
            "strategy_validation": {},
            "total_drug_documents": 0,
        }

        try:
            # Get ALL documents and filter in Python
            all_docs = self.memory_manager.collection.get(include=["metadatas", "documents"])

            print(f"[INFO] Total documents in memory: {len(all_docs.get('metadatas', []))}")

            # Filter for drug-related documents
            drug_docs = {"metadatas": [], "documents": []}

            if all_docs and all_docs["metadatas"]:
                for i, metadata in enumerate(all_docs["metadatas"]):
                    # Check if drug is mentioned
                    drug_names_context = metadata.get("drug_names_context", [])
                    drug_name_field = metadata.get("drug_name", "")

                    drug_found = False

                    # Handle both list and string formats for drug_names_context
                    if isinstance(drug_names_context, list):
                        drug_found = any(drug_name.lower() in str(name).lower() for name in drug_names_context)
                    elif isinstance(drug_names_context, str):
                        drug_found = drug_name.lower() in drug_names_context.lower()

                    # Also check the drug_name field
                    if not drug_found and drug_name_field:
                        drug_found = drug_name.lower() in drug_name_field.lower()

                    # Also check document content
                    if not drug_found and i < len(all_docs.get("documents", [])):
                        doc_content = all_docs["documents"][i]
                        if doc_content and drug_name.lower() in doc_content.lower():
                            drug_found = True

                    if drug_found:
                        drug_docs["metadatas"].append(metadata)
                        if i < len(all_docs.get("documents", [])):
                            drug_docs["documents"].append(all_docs["documents"][i])

            analysis["total_drug_documents"] = len(drug_docs["metadatas"])

            if drug_docs["metadatas"]:
                print(f"[OK] Found {len(drug_docs['metadatas'])} documents for {drug_name}")

                # Analyze documents
                workflow_counts = defaultdict(int)
                for metadata in drug_docs["metadatas"]:
                    # Check reference count
                    ref_count = metadata.get("reference_count", 1)
                    quality = "high" if ref_count >= 2 else "standard"
                    analysis["quality_distribution"][quality] = analysis["quality_distribution"].get(quality, 0) + 1

                    # Count workflows
                    workflows = metadata.get("referenced_in_workflows", [])
                    for wf in workflows:
                        workflow_counts[wf] += 1

                    # Check for cross-drug evidence
                    drug_context = metadata.get("drug_names_context", [])
                    if isinstance(drug_context, list) and len(drug_context) > 1:
                        analysis["cross_drug_evidence"].append(
                            {
                                "id": metadata.get("canonical_id", "unknown"),
                                "drugs": drug_context,
                                "workflows": workflows,
                                "source_type": metadata.get("source_type", "unknown"),
                            }
                        )

                # Calculate new vs updated
                analysis["new_documents"] = len(
                    [m for m in drug_docs["metadatas"] if len(m.get("referenced_in_workflows", [])) == 1]
                )
                analysis["updated_documents"] = len(drug_docs["metadatas"]) - analysis["new_documents"]

                # Show workflow distribution
                if workflow_counts:
                    print("\n[INFO] Documents by workflow:")
                    for wf, count in sorted(workflow_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                        print(f"  - {wf[:20]}...: {count} docs")

            else:
                print(f"[WARNING] No documents found for {drug_name}")

            # Validate strategy effectiveness
            planner_strategy = self.analysis_results["planner_performance"].get("strategy_determined")
            if planner_strategy:
                # Get analytics for drug class patterns
                analytics = self.memory_manager.get_document_usage_analytics()

                # Check for SGLT2 inhibitor pattern
                sglt2_drugs = [
                    "canagliflozin",
                    "dapagliflozin",
                    "empagliflozin",
                    "ertugliflozin",
                    "sotagliflozin",
                ]
                is_sglt2 = any(drug in drug_name.lower() for drug in sglt2_drugs)

                if is_sglt2:
                    # Count SGLT2 documents across all drugs
                    sglt2_count = 0
                    sglt2_breakdown = {}

                    for sglt2_drug in sglt2_drugs:
                        drug_pattern = analytics.get("drug_class_patterns", {}).get(sglt2_drug.title(), {})
                        drug_count = drug_pattern.get("document_count", 0)
                        if drug_count > 0:
                            sglt2_breakdown[sglt2_drug.title()] = drug_count
                            sglt2_count += drug_count

                    analysis["strategy_validation"] = {
                        "strategy_used": planner_strategy,
                        "drug_class": "SGLT2 Inhibitor",
                        "class_documents": sglt2_count,
                        "class_breakdown": sglt2_breakdown,
                        "strategy_appropriate": (
                            planner_strategy == "comprehensive"
                            if sglt2_count < 20
                            else planner_strategy in ["focused", "update"]
                        ),
                    }

                    print("\n[INFO] SGLT2 Inhibitor class analysis:")
                    print(f"  - Total SGLT2 documents: {sglt2_count}")
                    for drug, count in sglt2_breakdown.items():
                        print(f"  - {drug}: {count} documents")

                else:
                    analysis["strategy_validation"] = {
                        "strategy_used": planner_strategy,
                        "drug_class": "Other",
                        "strategy_appropriate": True,  # Can't validate without knowing the class
                    }

                print(
                    f"\n[OK] Strategy validation: {planner_strategy} strategy was {'appropriate' if analysis['strategy_validation']['strategy_appropriate'] else 'questionable'}"
                )

        except Exception as e:
            print(f"[ERROR] Error analyzing memory impact: {e}")
            import traceback

            traceback.print_exc()

        self.analysis_results["memory_utilization"] = analysis
        return analysis

    def generate_recommendations(self, drug_name: str) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []

        # Based on planner performance
        planner = self.analysis_results.get("planner_performance", {})
        if not planner:
            recommendations.append(
                f"No planner logs found - ensure logs are retained and check log directory: {self.logs_dir}"
            )
        elif planner.get("fallback_used"):
            recommendations.append(
                "Consider improving GPT-4 prompt reliability or implementing better fallback handling"
            )

        if planner.get("enhanced_features_used"):
            recommendations.append("[OK] Enhanced Memory Manager V2.0 is active - advanced features available")

        # Check if we analyzed the correct drug
        if planner.get("entities_extracted", {}).get("primary_drug"):
            extracted_drug = planner["entities_extracted"]["primary_drug"]
            if drug_name and extracted_drug.lower() != drug_name.lower():
                recommendations.append(
                    f"[CRITICAL] Analysis may be for wrong drug: extracted '{extracted_drug}' but expected '{drug_name}'"
                )
                recommendations.append("[ACTION] Verify log selection or use --planner-log to specify correct log file")

        # Check log selection confidence
        log_metadata = self.analysis_results.get("log_analysis_metadata", {})
        planner_metadata = log_metadata.get("planner_agent", {})
        if planner_metadata:
            score = planner_metadata.get("score", 0)
            if score < 30:
                recommendations.append(
                    f"[WARNING] Low confidence in log selection (score: {score:.1f}). Consider using --planner-log parameter"
                )

        # Based on strategy
        strategy = planner.get("strategy_determined", "unknown")
        memory_util = self.analysis_results.get("memory_utilization", {})

        if strategy == "unknown":
            recommendations.append("Strategy detection failed - check planner logs for errors")
        elif drug_name and (
            "sglt2" in drug_name.lower()
            or drug_name.lower()
            in [
                "canagliflozin",
                "dapagliflozin",
                "empagliflozin",
                "ertugliflozin",
                "sotagliflozin",
            ]
        ):
            total_docs = memory_util.get("strategy_validation", {}).get("class_documents", 0)
            if total_docs > 30 and strategy == "comprehensive":
                recommendations.append(
                    f"Consider using 'focused' or 'update' strategy for SGLT2 inhibitors (already have {total_docs} docs)"
                )
            elif strategy in ["focused", "update"]:
                recommendations.append(
                    f"[OK] Good strategy choice! Using '{strategy}' strategy for well-studied drug class"
                )

        # Based on workflow efficiency
        workflow = self.analysis_results.get("workflow_efficiency", {})
        total_data = sum(workflow.get("data_retrieved", {}).values())
        if total_data > 0:
            recommendations.append(f"[OK] Successfully retrieved {total_data} data items - good API connectivity")
        else:
            recommendations.append("No data retrieval detected - check API connectivity and logs")

        # Based on memory utilization
        total_docs = memory_util.get("total_drug_documents", 0)
        if total_docs > 0:
            recommendations.append(f"[OK] Total {drug_name} documents in memory: {total_docs}")

        if memory_util.get("new_documents", 0) > 0:
            recommendations.append(f"[OK] Successfully stored {memory_util['new_documents']} new documents in memory")

        cross_drug_count = len(memory_util.get("cross_drug_evidence", []))
        if cross_drug_count > 0:
            recommendations.append(f"[OK] Building cross-drug knowledge: {cross_drug_count} shared documents")
            # Show some examples
            examples = memory_util["cross_drug_evidence"][:2]
            for ex in examples:
                drugs = ", ".join(ex.get("drugs", [])[:3])
                recommendations.append(f"     Example: Document shared by {drugs}")

        # Next test recommendations
        if drug_name:
            if drug_name.lower() == "empagliflozin":
                recommendations.append("Next: Test Canagliflozin (another SGLT2) - should trigger 'focused' strategy")
            elif drug_name.lower() == "canagliflozin":
                recommendations.append("Next: Test Dapagliflozin (3rd SGLT2) - should trigger 'update' strategy")
            elif drug_name.lower() in [
                "dapagliflozin",
                "ertugliflozin",
                "sotagliflozin",
            ]:
                recommendations.append(
                    "Next: Test a different drug class (e.g., Lisinopril) - should trigger 'comprehensive' strategy"
                )

        # Log naming recommendations
        recommendations.append("\n[TIP] For better analysis accuracy, use unique log names per workflow:")
        recommendations.append("     Example: planner_agent_Sotagliflozin_WORKFLOWID.log")

        self.analysis_results["recommendations"] = recommendations
        return recommendations

    async def run_complete_analysis(
        self,
        workflow_id: Optional[str] = None,
        drug_name: str = "Empagliflozin",
        planner_log: str = None,
        router_log: str = None,
        commander_log: str = None,
    ):
        """Run complete analysis of memory-augmented planner test"""
        print("\n" + "=" * 60)
        print("MEMORY-AUGMENTED PLANNER TEST ANALYSIS v4.0")
        print("=" * 60)
        print(f"Target Drug: {drug_name}")
        print(f"Workflow ID: {workflow_id or 'Latest'}")
        print(f"Logs Directory: {self.logs_dir}")

        if planner_log:
            print(f"Planner Log Override: {planner_log}")
        if router_log:
            print(f"Router Log Override: {router_log}")
        if commander_log:
            print(f"Commander Log Override: {commander_log}")

        print("=" * 60)

        # Initialize memory
        if not await self.initialize_memory():
            return

        # Run analyses
        self.analyze_planner_logs(workflow_id, drug_name, planner_log)
        self.analyze_workflow_execution(workflow_id, drug_name, router_log, commander_log)
        await self.analyze_memory_impact(drug_name)
        recommendations = self.generate_recommendations(drug_name)

        # Generate summary report
        print("\n" + "=" * 60)
        print("ANALYSIS SUMMARY")
        print("=" * 60)

        # Log selection confidence
        log_metadata = self.analysis_results.get("log_analysis_metadata", {})
        if log_metadata:
            print("\n[LOG SELECTION CONFIDENCE]:")
            for agent, metadata in log_metadata.items():
                print(f"  - {agent}: {metadata.get('selected_log')} (score: {metadata.get('score', 0):.1f})")

        # Strategy effectiveness
        strategy = self.analysis_results["planner_performance"].get("strategy_determined", "unknown")
        memory_augmented = (
            self.analysis_results["planner_performance"].get("plan_structure", {}).get("memory_augmented", False)
        )
        enhanced_features = self.analysis_results["planner_performance"].get("enhanced_features_used", False)

        print("\n[BRAIN] MEMORY-AUGMENTED PLANNING:")
        print(f"  - Strategy: {strategy}")
        print(f"  - Memory-Augmented: {memory_augmented}")
        print(f"  - Enhanced Features (V2.0): {enhanced_features}")
        print(f"  - GPT-4 Used: {self.analysis_results['planner_performance'].get('gpt4_called', False)}")
        print(f"  - Fallback Used: {self.analysis_results['planner_performance'].get('fallback_used', False)}")

        # Show extracted entities
        entities = self.analysis_results["planner_performance"].get("entities_extracted", {})
        if entities:
            print(f"  - Extracted Drug: {entities.get('primary_drug', 'N/A')}")
            print(f"  - Extracted Disease: {entities.get('primary_disease', 'N/A')}")

        print("\n[CHART] WORKFLOW EXECUTION:")
        print(f"  - Completed: {self.analysis_results['workflow_efficiency'].get('workflow_completed', False)}")
        print(f"  - Steps Executed: {len(self.analysis_results['workflow_efficiency'].get('steps_executed', []))}")
        print(
            f"  - Total Data Retrieved: {sum(self.analysis_results['workflow_efficiency'].get('data_retrieved', {}).values())}"
        )

        # Show data breakdown
        data_retrieved = self.analysis_results["workflow_efficiency"].get("data_retrieved", {})
        if any(data_retrieved.values()):
            print(f"    - PubMed Articles: {data_retrieved.get('pubmed_articles', 0)}")
            print(f"    - Clinical Trials: {data_retrieved.get('clinical_trials', 0)}")
            print(f"    - Adverse Events: {data_retrieved.get('adverse_events', 0)}")

        print(f"  - PDF Generated: {self.analysis_results['workflow_efficiency'].get('pdf_generated', False)}")

        print("\n[DISK] MEMORY IMPACT:")
        print(
            f"  - Total {drug_name} Documents: {self.analysis_results['memory_utilization'].get('total_drug_documents', 0)}"
        )
        print(f"  - New Documents: {self.analysis_results['memory_utilization'].get('new_documents', 0)}")
        print(f"  - Updated Documents: {self.analysis_results['memory_utilization'].get('updated_documents', 0)}")
        print(
            f"  - Cross-Drug Evidence: {len(self.analysis_results['memory_utilization'].get('cross_drug_evidence', []))}"
        )
        print(
            f"  - High-Quality Docs: {self.analysis_results['memory_utilization'].get('quality_distribution', {}).get('high', 0)}"
        )

        # Show SGLT2 breakdown if available
        validation = self.analysis_results["memory_utilization"].get("strategy_validation", {})
        if validation.get("class_breakdown"):
            print("\n  SGLT2 Class Distribution:")
            for drug, count in validation["class_breakdown"].items():
                print(f"    - {drug}: {count} documents")

        print("\n[CLIPBOARD] RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            if rec.startswith("\n"):
                print(rec)
            else:
                print(f"  {i}. {rec}")

        # Save detailed results
        results_dir = Path(project_root) / "analysis_results"
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"memory_planner_analysis_{drug_name}_{timestamp}.json"

        try:
            with open(results_file, "w") as f:
                json.dump(self.analysis_results, f, indent=2, default=str)

            print(f"\n[OK] Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"\n[ERROR] Could not save results file: {e}")

        return self.analysis_results


def main():
    """Main function with argparse support"""
    parser = argparse.ArgumentParser(
        description="Analyze Memory-Augmented Planner test results (v4.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python analyze_memory_planner_test.py --drug Sotagliflozin
  
  # With workflow ID
  python analyze_memory_planner_test.py --drug Empagliflozin --workflow 687839be-3d1a-47ef-aa90-a246c7eabae6
  
  # With specific log files
  python analyze_memory_planner_test.py --drug Sotagliflozin --planner-log planner_agent_Sota_FRESH.log
  
  # With full paths
  python analyze_memory_planner_test.py -d Canagliflozin --planner-log "C:\\logs\\planner_agent_Cana.log"
        """,
    )

    parser.add_argument(
        "-d",
        "--drug",
        type=str,
        default="Empagliflozin",
        help="Drug name to analyze (default: Empagliflozin)",
    )

    parser.add_argument(
        "-w",
        "--workflow",
        type=str,
        default=None,
        help="Specific workflow ID to analyze (default: latest)",
    )

    parser.add_argument("--logs-dir", type=str, default=None, help="Override logs directory path")

    parser.add_argument(
        "--planner-log",
        type=str,
        default=None,
        help="Specific planner log file to analyze (path or filename)",
    )

    parser.add_argument(
        "--router-log",
        type=str,
        default=None,
        help="Specific router log file to analyze (path or filename)",
    )

    parser.add_argument(
        "--commander-log",
        type=str,
        default=None,
        help="Specific commander log file to analyze (path or filename)",
    )

    args = parser.parse_args()

    # Create analyzer
    analyzer = MemoryPlannerAnalyzer()

    # Override logs directory if specified
    if args.logs_dir:
        analyzer.logs_dir = Path(args.logs_dir)
        print(f"[INFO] Using custom logs directory: {analyzer.logs_dir}")

    # Run analysis
    asyncio.run(
        analyzer.run_complete_analysis(
            workflow_id=args.workflow,
            drug_name=args.drug,
            planner_log=args.planner_log,
            router_log=args.router_log,
            commander_log=args.commander_log,
        )
    )


if __name__ == "__main__":
    main()
