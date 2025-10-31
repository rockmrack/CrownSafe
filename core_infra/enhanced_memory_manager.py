"""
EnhancedMemoryManager V2.0 - Advanced Memory with Temporal Analysis & Contradiction Detection
Built on MVP-1.4 foundation with sophisticated pharmaceutical research intelligence
ENHANCED: Fixed get_enhanced_research_recommendations with proper similarity search and debugging
"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import openai
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .memory_manager import MemoryManager  # Inherit from MVP-1.4

logger = logging.getLogger(__name__)


@dataclass
class TemporalPattern:
    """Represents a temporal research pattern"""

    pattern_id: str
    entity: str  # Drug name, indication, etc.
    timeframe: str  # "recent", "historical", "emerging"
    trend_direction: str  # "increasing", "decreasing", "stable"
    evidence_count: int
    confidence_score: float
    first_seen: datetime
    last_updated: datetime
    supporting_evidence: List[str] = field(default_factory=list)


@dataclass
class Contradiction:
    """Represents conflicting evidence in research"""

    contradiction_id: str
    entity: str
    conflicting_claims: List[str]
    evidence_sources: List[str]
    severity: str  # "minor", "moderate", "major"
    confidence_score: float
    detected_at: datetime
    resolution_suggestions: List[str] = field(default_factory=list)


@dataclass
class ResearchGap:
    """Represents identified research gaps"""

    gap_id: str
    entity: str
    gap_type: str  # "clinical_trial", "safety_data", "mechanism", "population"
    description: str
    priority_score: float
    suggested_research: List[str]
    identified_at: datetime


@dataclass
class CrossWorkflowInsight:
    """Advanced insights from cross-workflow analysis"""

    insight_id: str
    insight_type: str  # "drug_class_pattern", "indication_synergy", "safety_correlation"
    entities_involved: List[str]
    insight_description: str
    confidence_score: float
    supporting_workflows: List[str]
    actionable_recommendations: List[str]
    generated_at: datetime


class EnhancedMemoryManager(MemoryManager):
    """
    Enhanced Memory Manager V2.0

    Extends MVP-1.4 with:
    - Temporal pattern analysis
    - Contradiction detection
    - Research gap identification
    - Advanced cross-workflow insights
    - ENHANCED: Improved research recommendations with similarity search
    """

    def __init__(
        self,
        chroma_db_path: str = "chroma_db_data",
        collection_name: str = "cureviax_knowledge_base_v1",
        logger_instance: Optional[logging.Logger] = None,
    ):
        """Initialize Enhanced Memory Manager"""

        # Initialize parent class first
        super().__init__(
            logger_instance=logger_instance,
            chroma_db_path=chroma_db_path,
            collection_name=collection_name,
        )

        # Enhanced collections for advanced features
        self.temporal_patterns: Dict[str, TemporalPattern] = {}
        self.contradictions: Dict[str, Contradiction] = {}
        self.research_gaps: Dict[str, ResearchGap] = {}
        self.cross_workflow_insights: Dict[str, CrossWorkflowInsight] = {}

        # Analysis caches
        self._temporal_analysis_cache = {}
        self._contradiction_cache = {}
        self._gap_analysis_cache = {}

        # ENHANCED: Similarity search thresholds for research recommendations
        self.similarity_thresholds = {
            "excellent_match": 0.12,  # Very similar (likely same drug class)
            "good_match": 0.20,  # Good similarity (related drugs)
            "moderate_match": 0.30,  # Moderate similarity (some relevance)
            "weak_match": 0.40,  # Weak similarity (minimal relevance)
        }

        # Initialize enhanced collections in ChromaDB
        if self.chroma_client and self.collection:
            self._init_enhanced_collections()
            self.logger.info(
                "EnhancedMemoryManager V2.0 initialized with temporal analysis and contradiction detection"
            )
        else:
            self.logger.error("Failed to initialize EnhancedMemoryManager - base MemoryManager initialization failed")

    def _init_enhanced_collections(self):
        """Initialize additional ChromaDB collections for enhanced features"""
        try:
            # FIXED: Use self.chroma_client instead of self.client
            # Temporal patterns collection
            self.temporal_collection = self.chroma_client.get_or_create_collection(
                name=f"{self.collection_name}_temporal",
                metadata={"hnsw:space": "cosine"},
            )

            # Contradictions collection
            self.contradictions_collection = self.chroma_client.get_or_create_collection(
                name=f"{self.collection_name}_contradictions",
                metadata={"hnsw:space": "cosine"},
            )

            # Research gaps collection
            self.gaps_collection = self.chroma_client.get_or_create_collection(
                name=f"{self.collection_name}_gaps", metadata={"hnsw:space": "cosine"}
            )

            # Cross-workflow insights collection
            self.insights_collection = self.chroma_client.get_or_create_collection(
                name=f"{self.collection_name}_insights",
                metadata={"hnsw:space": "cosine"},
            )

            self.logger.info("Enhanced collections initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced collections: {e}")
            # Set collections to None if initialization fails
            self.temporal_collection = None
            self.contradictions_collection = None
            self.gaps_collection = None
            self.insights_collection = None

    async def store_workflow_outputs_enhanced(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced workflow storage with temporal analysis and contradiction detection
        """
        self.logger.info("Starting enhanced workflow storage with advanced analysis")

        # First, perform standard storage from MVP-1.4
        # Convert async call to sync for compatibility
        if hasattr(workflow_data, "get"):
            # Extract parameters for standard storage
            workflow_id = workflow_data.get("workflow_id", f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            goal = workflow_data.get("goal", "Enhanced workflow")
            entities = workflow_data.get("extracted_entities", {})
            research_data = workflow_data.get("research_data", {})
            pdf_path = workflow_data.get("pdf_path")
            timestamp = workflow_data.get("completion_timestamp", datetime.now().isoformat())

            standard_result = self.store_workflow_outputs(
                workflow_id=workflow_id,
                user_goal=goal,
                extracted_entities=entities,
                pubmed_results_payload=research_data.get("pubmed"),
                pdf_path=pdf_path,
                completion_timestamp=timestamp,
            )
        else:
            # Fallback for invalid input
            standard_result = {
                "status": "error",
                "message": "Invalid workflow data format",
            }

        # Then perform enhanced analysis
        enhanced_results = {
            "standard_storage": standard_result,
            "temporal_analysis": {},
            "contradiction_detection": {},
            "gap_analysis": {},
            "cross_workflow_insights": {},
        }

        try:
            # Extract entities for analysis
            entities = self._extract_entities_enhanced(workflow_data)

            # Temporal pattern analysis
            temporal_results = await self._analyze_temporal_patterns(entities, workflow_data)
            enhanced_results["temporal_analysis"] = temporal_results

            # Contradiction detection
            contradiction_results = await self._detect_contradictions(entities, workflow_data)
            enhanced_results["contradiction_detection"] = contradiction_results

            # Research gap identification
            gap_results = await self._identify_research_gaps(entities, workflow_data)
            enhanced_results["gap_analysis"] = gap_results

            # Cross-workflow insights
            insight_results = await self._generate_cross_workflow_insights(entities, workflow_data)
            enhanced_results["cross_workflow_insights"] = insight_results

            self.logger.info("Enhanced workflow storage completed successfully")
            return enhanced_results

        except Exception as e:
            self.logger.error(f"Enhanced analysis failed: {e}")
            # Return standard results if enhanced analysis fails
            enhanced_results["error"] = str(e)
            return enhanced_results

    def _extract_entities_enhanced(self, workflow_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Enhanced entity extraction for temporal and contradiction analysis"""
        entities = {
            "drugs": [],
            "indications": [],
            "outcomes": [],
            "populations": [],
            "timeframes": [],
        }

        try:
            # Extract from goal
            goal = workflow_data.get("goal", "")

            # Drug extraction (improved)
            drug_patterns = [
                r"\b([A-Z][a-z]+(?:flozin|pril|sartan|olol|dipine|statin))\b",  # Common drug suffixes
                r"\b([A-Z][a-z]{4,})\s+(?:for|in|treatment)",  # Capitalized words before treatment contexts
                r"(?:drug|medication|compound)\s+([A-Z][a-z]+)",
            ]

            for pattern in drug_patterns:
                matches = re.findall(pattern, goal, re.IGNORECASE)
                entities["drugs"].extend(matches)

            # Indication extraction
            indication_patterns = [
                r"(?:for|treating|treatment of)\s+([A-Z][a-z\s]+?)(?:\s*[,.]|$)",
                r"\b(heart failure|diabetes|hypertension|kidney disease|CKD)\b",
                r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:patients|treatment)",
            ]

            for pattern in indication_patterns:
                matches = re.findall(pattern, goal, re.IGNORECASE)
                entities["indications"].extend(matches)

            # Extract from research data
            research_data = workflow_data.get("research_data", {})
            for agent_data in research_data.values():
                if isinstance(agent_data, dict):
                    content = str(agent_data.get("content", ""))

                    # Extract outcome measures
                    outcome_patterns = [
                        r"\b(efficacy|safety|mortality|hospitalization|adverse events)\b",
                        r"\b(primary endpoint|secondary endpoint|outcome measure)\b",
                    ]

                    for pattern in outcome_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        entities["outcomes"].extend(matches)

            # Clean and deduplicate
            for key in entities:
                entities[key] = list(set([e.strip() for e in entities[key] if e.strip()]))

            self.logger.info(f"Enhanced entity extraction completed: {entities}")
            return entities

        except Exception as e:
            self.logger.error(f"Enhanced entity extraction failed: {e}")
            return entities

    async def _analyze_temporal_patterns(
        self, entities: Dict[str, List[str]], workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze temporal patterns in research data"""
        self.logger.info("Starting temporal pattern analysis")

        temporal_results = {
            "patterns_detected": [],
            "trend_analysis": {},
            "temporal_insights": [],
        }

        try:
            current_time = datetime.now()

            # Analyze each drug entity
            for drug in entities.get("drugs", []):
                # Get historical data for this drug
                historical_docs = await self._get_historical_documents(drug)

                if len(historical_docs) >= 2:  # Need at least 2 time points
                    pattern = await self._detect_temporal_pattern(drug, historical_docs, current_time)
                    if pattern:
                        temporal_results["patterns_detected"].append(
                            {
                                "entity": drug,
                                "pattern_type": pattern.trend_direction,
                                "confidence": pattern.confidence_score,
                                "timeframe": pattern.timeframe,
                            }
                        )

                        # Store pattern
                        self.temporal_patterns[pattern.pattern_id] = pattern

            # Generate temporal insights
            temporal_results["temporal_insights"] = await self._generate_temporal_insights(entities)

            self.logger.info(
                f"Temporal analysis completed: {len(temporal_results['patterns_detected'])} patterns detected"
            )
            return temporal_results

        except Exception as e:
            self.logger.error(f"Temporal pattern analysis failed: {e}")
            return temporal_results

    async def _get_historical_documents(self, entity: str) -> List[Dict[str, Any]]:
        """Retrieve historical documents for temporal analysis"""
        try:
            # Query for documents containing the entity
            results = self.collection.query(
                query_texts=[entity],
                n_results=50,  # Get more results for temporal analysis
                include=["documents", "metadatas"],
            )

            documents = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                    # Extract temporal information
                    doc_data = {
                        "content": doc,
                        "metadata": metadata,
                        "timestamp": self._extract_timestamp(metadata),
                        "entity": entity,
                    }
                    documents.append(doc_data)

            # Sort by timestamp
            documents.sort(key=lambda x: x["timestamp"] or datetime.min)
            return documents

        except Exception as e:
            self.logger.error(f"Failed to retrieve historical documents for {entity}: {e}")
            return []

    def _extract_timestamp(self, metadata: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from document metadata"""
        try:
            # Try various timestamp fields
            timestamp_fields = ["timestamp", "created_at", "publication_date", "date"]

            for field in timestamp_fields:
                if field in metadata:
                    timestamp_str = metadata[field]
                    if isinstance(timestamp_str, str):
                        # Try parsing common formats
                        formats = [
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d",
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%dT%H:%M:%S.%f",
                        ]

                        for fmt in formats:
                            try:
                                return datetime.strptime(timestamp_str, fmt)
                            except ValueError:
                                continue

            return None

        except Exception as e:
            self.logger.error(f"Failed to extract timestamp from metadata: {e}")
            return None

    async def _detect_temporal_pattern(
        self, entity: str, historical_docs: List[Dict[str, Any]], current_time: datetime
    ) -> Optional[TemporalPattern]:
        """Detect temporal patterns in historical documents"""
        try:
            if len(historical_docs) < 2:
                return None

            # Analyze research volume over time
            time_buckets = defaultdict(int)

            for doc in historical_docs:
                timestamp = doc["timestamp"]
                if timestamp:
                    # Bucket by month
                    month_key = timestamp.strftime("%Y-%m")
                    time_buckets[month_key] += 1

            if len(time_buckets) < 2:
                return None

            # Calculate trend
            sorted_months = sorted(time_buckets.keys())
            early_counts = sum(time_buckets[month] for month in sorted_months[: len(sorted_months) // 2])
            recent_counts = sum(time_buckets[month] for month in sorted_months[len(sorted_months) // 2 :])

            # Determine trend direction
            if recent_counts > early_counts * 1.2:
                trend_direction = "increasing"
                confidence = min(0.9, (recent_counts - early_counts) / early_counts)
            elif recent_counts < early_counts * 0.8:
                trend_direction = "decreasing"
                confidence = min(0.9, (early_counts - recent_counts) / early_counts)
            else:
                trend_direction = "stable"
                confidence = 0.6

            # Create pattern
            pattern = TemporalPattern(
                pattern_id=f"temporal_{entity}_{current_time.strftime('%Y%m%d')}",
                entity=entity,
                timeframe="recent" if len(sorted_months) <= 6 else "historical",
                trend_direction=trend_direction,
                evidence_count=len(historical_docs),
                confidence_score=confidence,
                first_seen=historical_docs[0]["timestamp"] or current_time,
                last_updated=current_time,
                supporting_evidence=[doc["content"][:200] for doc in historical_docs[:3]],
            )

            return pattern

        except Exception as e:
            self.logger.error(f"Failed to detect temporal pattern for {entity}: {e}")
            return None

    async def _generate_temporal_insights(self, entities: Dict[str, List[str]]) -> List[str]:
        """Generate actionable temporal insights"""
        insights = []

        try:
            # Analyze patterns across all detected temporal patterns
            increasing_trends = [p for p in self.temporal_patterns.values() if p.trend_direction == "increasing"]
            decreasing_trends = [p for p in self.temporal_patterns.values() if p.trend_direction == "decreasing"]

            if increasing_trends:
                insights.append(f"Emerging research interest detected in {len(increasing_trends)} entities")

            if decreasing_trends:
                insights.append(f"Declining research activity noted for {len(decreasing_trends)} entities")

            # Drug-specific insights
            for drug in entities.get("drugs", []):
                if drug in [p.entity for p in self.temporal_patterns.values()]:
                    pattern = next(p for p in self.temporal_patterns.values() if p.entity == drug)
                    if pattern.confidence_score > 0.7:
                        insights.append(
                            f"{drug}: {pattern.trend_direction} research trend (confidence: {pattern.confidence_score:.2f})"
                        )

            return insights

        except Exception as e:
            self.logger.error(f"Failed to generate temporal insights: {e}")
            return insights

    async def _detect_contradictions(
        self, entities: Dict[str, List[str]], workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect contradictory evidence across research"""
        self.logger.info("Starting contradiction detection")

        contradiction_results = {
            "contradictions_found": [],
            "confidence_scores": {},
            "resolution_suggestions": [],
        }

        try:
            for drug in entities.get("drugs", []):
                contradictions = await self._find_contradictory_evidence(drug)

                for contradiction in contradictions:
                    contradiction_results["contradictions_found"].append(
                        {
                            "entity": drug,
                            "contradiction_type": contradiction.severity,
                            "conflicting_claims": contradiction.conflicting_claims,
                            "confidence": contradiction.confidence_score,
                        }
                    )

                    # Store contradiction
                    self.contradictions[contradiction.contradiction_id] = contradiction

            # Generate resolution suggestions
            contradiction_results["resolution_suggestions"] = await self._suggest_contradiction_resolutions()

            self.logger.info(
                f"Contradiction detection completed: {len(contradiction_results['contradictions_found'])} contradictions found"
            )
            return contradiction_results

        except Exception as e:
            self.logger.error(f"Contradiction detection failed: {e}")
            return contradiction_results

    async def _find_contradictory_evidence(self, entity: str) -> List[Contradiction]:
        """Find contradictory evidence for a specific entity"""
        contradictions = []

        try:
            # Get all documents related to the entity
            results = self.collection.query(
                query_texts=[f"{entity} efficacy safety"],
                n_results=20,
                include=["documents", "metadatas"],
            )

            if not results["documents"] or not results["documents"][0]:
                return contradictions

            documents = results["documents"][0]

            # Look for contradictory statements
            efficacy_statements = []
            safety_statements = []

            for doc in documents:
                # Extract efficacy claims
                efficacy_patterns = [
                    r"(effective|ineffective|superior|inferior)\s+(?:for|in|at)",
                    r"(significant|no significant|marginal)\s+(?:improvement|benefit|effect)",
                    r"(reduces|increases|no effect on)\s+(?:risk|mortality|hospitalization)",
                ]

                for pattern in efficacy_patterns:
                    matches = re.findall(pattern, doc, re.IGNORECASE)
                    efficacy_statements.extend([(match, doc[:100]) for match in matches])

                # Extract safety claims
                safety_patterns = [
                    r"(safe|unsafe|well-tolerated|poorly tolerated)",
                    r"(adverse events|side effects|complications)\s+(rare|common|frequent)",
                    r"(contraindicated|recommended|approved)\s+(?:for|in)",
                ]

                for pattern in safety_patterns:
                    matches = re.findall(pattern, doc, re.IGNORECASE)
                    safety_statements.extend([(match, doc[:100]) for match in matches])

            # Detect contradictions in efficacy
            contradictions.extend(await self._analyze_statement_contradictions(entity, "efficacy", efficacy_statements))

            # Detect contradictions in safety
            contradictions.extend(await self._analyze_statement_contradictions(entity, "safety", safety_statements))

            return contradictions

        except Exception as e:
            self.logger.error(f"Failed to find contradictory evidence for {entity}: {e}")
            return contradictions

    async def _analyze_statement_contradictions(
        self, entity: str, category: str, statements: List[Tuple[str, str]]
    ) -> List[Contradiction]:
        """Analyze statements for contradictions"""
        contradictions = []

        try:
            if len(statements) < 2:
                return contradictions

            # Simple contradiction detection based on opposing terms
            opposing_terms = {
                "effective": ["ineffective", "no effect"],
                "safe": ["unsafe", "contraindicated"],
                "significant": ["no significant", "marginal"],
                "reduces": ["increases", "no effect on"],
                "superior": ["inferior", "equivalent"],
            }

            for i, (statement1, source1) in enumerate(statements):
                for j, (statement2, source2) in enumerate(statements[i + 1 :], i + 1):
                    # Check for opposing terms
                    contradiction_found = False
                    conflicting_claims = []

                    for positive_term, negative_terms in opposing_terms.items():
                        if positive_term.lower() in statement1.lower() and any(
                            neg_term.lower() in statement2.lower() for neg_term in negative_terms
                        ):
                            contradiction_found = True
                            conflicting_claims = [statement1, statement2]
                            break
                        elif positive_term.lower() in statement2.lower() and any(
                            neg_term.lower() in statement1.lower() for neg_term in negative_terms
                        ):
                            contradiction_found = True
                            conflicting_claims = [statement2, statement1]
                            break

                    if contradiction_found:
                        contradiction = Contradiction(
                            contradiction_id=f"contradiction_{entity}_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            entity=entity,
                            conflicting_claims=conflicting_claims,
                            evidence_sources=[source1, source2],
                            severity="moderate",  # Default severity
                            confidence_score=0.7,  # Default confidence
                            detected_at=datetime.now(),
                            resolution_suggestions=[
                                "Review study methodologies for differences",
                                "Consider population or dosage differences",
                                "Look for temporal factors in studies",
                            ],
                        )
                        contradictions.append(contradiction)

            return contradictions

        except Exception as e:
            self.logger.error(f"Failed to analyze statement contradictions for {entity}: {e}")
            return contradictions

    async def _suggest_contradiction_resolutions(self) -> List[str]:
        """Suggest ways to resolve detected contradictions"""
        suggestions = []

        try:
            if not self.contradictions:
                return ["No contradictions detected - evidence appears consistent"]

            # General resolution strategies
            suggestions.extend(
                [
                    "Compare study populations and inclusion criteria",
                    "Analyze dosage and administration differences",
                    "Review study duration and follow-up periods",
                    "Consider publication dates and methodological advances",
                    "Examine endpoint definitions and measurement methods",
                ]
            )

            # Specific suggestions based on contradiction patterns
            entity_contradictions = defaultdict(list)
            for contradiction in self.contradictions.values():
                entity_contradictions[contradiction.entity].append(contradiction)

            for entity, contradictions in entity_contradictions.items():
                if len(contradictions) > 2:
                    suggestions.append(
                        f"Consider systematic review of {entity} literature due to multiple contradictions"
                    )

                severity_counts = Counter(c.severity for c in contradictions)
                if severity_counts.get("major", 0) > 0:
                    suggestions.append(f"Prioritize resolution of major contradictions for {entity}")

            return suggestions

        except Exception as e:
            self.logger.error(f"Failed to suggest contradiction resolutions: {e}")
            return suggestions

    async def _identify_research_gaps(
        self, entities: Dict[str, List[str]], workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify gaps in current research"""
        self.logger.info("Starting research gap identification")

        gap_results = {
            "gaps_identified": [],
            "priority_areas": [],
            "research_suggestions": [],
        }

        try:
            for drug in entities.get("drugs", []):
                gaps = await self._analyze_research_gaps_for_entity(drug)

                for gap in gaps:
                    gap_results["gaps_identified"].append(
                        {
                            "entity": drug,
                            "gap_type": gap.gap_type,
                            "description": gap.description,
                            "priority": gap.priority_score,
                        }
                    )

                    # Store gap
                    self.research_gaps[gap.gap_id] = gap

            # Generate priority areas and suggestions
            gap_results["priority_areas"] = await self._prioritize_research_areas()
            gap_results["research_suggestions"] = await self._generate_research_suggestions()

            self.logger.info(f"Research gap analysis completed: {len(gap_results['gaps_identified'])} gaps identified")
            return gap_results

        except Exception as e:
            self.logger.error(f"Research gap identification failed: {e}")
            return gap_results

    async def _analyze_research_gaps_for_entity(self, entity: str) -> List[ResearchGap]:
        """Analyze research gaps for a specific entity"""
        gaps = []

        try:
            # Get all research for this entity
            results = self.collection.query(query_texts=[entity], n_results=30, include=["documents", "metadatas"])

            if not results["documents"] or not results["documents"][0]:
                # No research found - major gap
                gap = ResearchGap(
                    gap_id=f"gap_{entity}_no_research_{datetime.now().strftime('%Y%m%d')}",
                    entity=entity,
                    gap_type="comprehensive",
                    description=f"Limited research data available for {entity}",
                    priority_score=0.9,
                    suggested_research=[
                        f"Conduct systematic literature review for {entity}",
                        f"Design clinical trials for {entity} efficacy",
                        f"Investigate {entity} safety profile",
                    ],
                    identified_at=datetime.now(),
                )
                gaps.append(gap)
                return gaps

            documents = results["documents"][0]

            # Analyze content for specific gap types
            content_analysis = {
                "clinical_trials": 0,
                "safety_data": 0,
                "mechanism_studies": 0,
                "population_studies": 0,
                "long_term_studies": 0,
            }

            for doc in documents:
                doc_lower = doc.lower()

                # Count evidence types
                if any(term in doc_lower for term in ["clinical trial", "randomized", "controlled study"]):
                    content_analysis["clinical_trials"] += 1

                if any(term in doc_lower for term in ["adverse events", "side effects", "safety", "toxicity"]):
                    content_analysis["safety_data"] += 1

                if any(term in doc_lower for term in ["mechanism", "pathway", "molecular", "pharmacology"]):
                    content_analysis["mechanism_studies"] += 1

                if any(
                    term in doc_lower
                    for term in [
                        "population",
                        "demographic",
                        "subgroup",
                        "elderly",
                        "pediatric",
                    ]
                ):
                    content_analysis["population_studies"] += 1

                if any(term in doc_lower for term in ["long-term", "follow-up", "longitudinal", "years"]):
                    content_analysis["long_term_studies"] += 1

            # Identify gaps based on low counts
            total_docs = len(documents)
            gap_thresholds = {
                "clinical_trials": 0.3,  # Less than 30% of docs mention trials
                "safety_data": 0.2,  # Less than 20% mention safety
                "mechanism_studies": 0.15,  # Less than 15% mention mechanism
                "population_studies": 0.1,  # Less than 10% mention populations
                "long_term_studies": 0.1,  # Less than 10% mention long-term
            }

            for gap_type, threshold in gap_thresholds.items():
                if content_analysis[gap_type] / total_docs < threshold:
                    priority_score = 1.0 - (content_analysis[gap_type] / total_docs) / threshold

                    gap = ResearchGap(
                        gap_id=f"gap_{entity}_{gap_type}_{datetime.now().strftime('%Y%m%d')}",
                        entity=entity,
                        gap_type=gap_type,
                        description=f"Limited {gap_type.replace('_', ' ')} data for {entity}",
                        priority_score=min(priority_score, 0.95),
                        suggested_research=self._generate_gap_specific_suggestions(entity, gap_type),
                        identified_at=datetime.now(),
                    )
                    gaps.append(gap)

            return gaps

        except Exception as e:
            self.logger.error(f"Failed to analyze research gaps for {entity}: {e}")
            return gaps

    def _generate_gap_specific_suggestions(self, entity: str, gap_type: str) -> List[str]:
        """Generate specific research suggestions for identified gaps"""
        suggestions_map = {
            "clinical_trials": [
                f"Design randomized controlled trial for {entity}",
                f"Conduct dose-response studies for {entity}",
                f"Investigate {entity} vs standard of care",
            ],
            "safety_data": [
                f"Conduct comprehensive safety analysis of {entity}",
                f"Study long-term adverse events of {entity}",
                f"Investigate drug interactions with {entity}",
            ],
            "mechanism_studies": [
                f"Investigate molecular mechanism of action for {entity}",
                f"Study pharmacokinetic properties of {entity}",
                f"Analyze cellular pathways affected by {entity}",
            ],
            "population_studies": [
                f"Study {entity} efficacy in diverse populations",
                f"Investigate {entity} use in elderly patients",
                f"Analyze {entity} outcomes by demographic factors",
            ],
            "long_term_studies": [
                f"Conduct long-term follow-up studies for {entity}",
                f"Investigate sustained efficacy of {entity}",
                f"Study long-term safety profile of {entity}",
            ],
        }

        return suggestions_map.get(gap_type, [f"Conduct additional research on {entity}"])

    async def _prioritize_research_areas(self) -> List[str]:
        """Prioritize identified research areas"""
        priority_areas = []

        try:
            # Sort gaps by priority score
            sorted_gaps = sorted(
                self.research_gaps.values(),
                key=lambda x: x.priority_score,
                reverse=True,
            )

            # Group by gap type
            gap_types = defaultdict(list)
            for gap in sorted_gaps:
                gap_types[gap.gap_type].append(gap)

            # Prioritize based on frequency and scores
            for gap_type, gaps in gap_types.items():
                if len(gaps) >= 2:  # Multiple entities have this gap
                    avg_priority = sum(g.priority_score for g in gaps) / len(gaps)
                    priority_areas.append(
                        f"{gap_type.replace('_', ' ').title()}: {len(gaps)} entities affected (avg priority: {avg_priority:.2f})"
                    )

            # Add high-priority individual gaps
            for gap in sorted_gaps[:3]:  # Top 3 individual gaps
                if gap.priority_score > 0.8:
                    priority_areas.append(f"High priority: {gap.description}")

            return priority_areas

        except Exception as e:
            self.logger.error(f"Failed to prioritize research areas: {e}")
            return priority_areas

    async def _generate_research_suggestions(self) -> List[str]:
        """Generate actionable research suggestions"""
        suggestions = []

        try:
            # Collect all suggestions from identified gaps
            all_suggestions = []
            for gap in self.research_gaps.values():
                all_suggestions.extend(gap.suggested_research)

            # Remove duplicates while preserving order
            seen = set()
            unique_suggestions = []
            for suggestion in all_suggestions:
                if suggestion not in seen:
                    seen.add(suggestion)
                    unique_suggestions.append(suggestion)

            # Prioritize based on gap priority scores (reserved for prioritization logic)
            _ = {gap.gap_id: gap.priority_score for gap in self.research_gaps.values()}

            # Take top suggestions
            suggestions = unique_suggestions[:10]  # Top 10 suggestions

            # Add general recommendations
            if len(self.research_gaps) > 5:
                suggestions.append("Consider systematic review to synthesize existing evidence")

            if any(gap.gap_type == "clinical_trials" for gap in self.research_gaps.values()):
                suggestions.append("Prioritize randomized controlled trials for high-impact questions")

            return suggestions

        except Exception as e:
            self.logger.error(f"Failed to generate research suggestions: {e}")
            return suggestions

    async def _generate_cross_workflow_insights(
        self, entities: Dict[str, List[str]], workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate advanced cross-workflow insights"""
        self.logger.info("Starting cross-workflow insight generation")

        insight_results = {
            "insights_generated": [],
            "pattern_discoveries": [],
            "recommendations": [],
        }

        try:
            # Analyze drug class patterns
            drug_class_insights = await self._analyze_drug_class_patterns(entities)
            insight_results["insights_generated"].extend(drug_class_insights)

            # Analyze indication synergies
            indication_insights = await self._analyze_indication_patterns(entities)
            insight_results["insights_generated"].extend(indication_insights)

            # Generate recommendations
            insight_results["recommendations"] = await self._generate_insight_recommendations()

            self.logger.info(
                f"Cross-workflow insight generation completed: {len(insight_results['insights_generated'])} insights generated"
            )
            return insight_results

        except Exception as e:
            self.logger.error(f"Cross-workflow insight generation failed: {e}")
            return insight_results

    async def _analyze_drug_class_patterns(self, entities: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Analyze patterns across drug classes"""
        insights = []

        try:
            # Get all documents to analyze drug class patterns
            all_results = self.collection.get()

            if not all_results["documents"]:
                return insights

            # Analyze SGLT2 inhibitor patterns (current focus)
            sglt2_drugs = [drug for drug in entities.get("drugs", []) if "flozin" in drug.lower()]

            if len(sglt2_drugs) >= 2:
                # Analyze common patterns
                common_outcomes = await self._find_common_outcomes(sglt2_drugs)
                _ = await self._find_common_indications(sglt2_drugs)  # common_indications

                if common_outcomes:
                    insight = CrossWorkflowInsight(
                        insight_id=f"sglt2_class_outcomes_{datetime.now().strftime('%Y%m%d')}",
                        insight_type="drug_class_pattern",
                        entities_involved=sglt2_drugs,
                        insight_description=f"SGLT2 inhibitors show consistent patterns in: {', '.join(common_outcomes)}",
                        confidence_score=0.8,
                        supporting_workflows=[f"workflow_{drug}" for drug in sglt2_drugs],
                        actionable_recommendations=[
                            "Consider class-wide efficacy assumptions for SGLT2 inhibitors",
                            "Focus research on differentiating factors within SGLT2 class",
                            "Leverage class knowledge for new SGLT2 inhibitor evaluation",
                        ],
                        generated_at=datetime.now(),
                    )

                    self.cross_workflow_insights[insight.insight_id] = insight
                    insights.append(
                        {
                            "type": "drug_class_pattern",
                            "description": insight.insight_description,
                            "confidence": insight.confidence_score,
                            "recommendations": insight.actionable_recommendations,
                        }
                    )

            return insights

        except Exception as e:
            self.logger.error(f"Failed to analyze drug class patterns: {e}")
            return insights

    async def _find_common_outcomes(self, drugs: List[str]) -> List[str]:
        """Find common outcomes across drugs"""
        outcome_patterns = defaultdict(int)

        try:
            for drug in drugs:
                results = self.collection.query(
                    query_texts=[f"{drug} outcomes efficacy"],
                    n_results=10,
                    include=["documents"],
                )

                if results["documents"] and results["documents"][0]:
                    for doc in results["documents"][0]:
                        # Extract outcome mentions
                        doc_lower = doc.lower()
                        outcomes = [
                            "cardiovascular outcomes",
                            "heart failure",
                            "kidney function",
                            "mortality",
                            "hospitalization",
                            "blood glucose",
                            "weight loss",
                        ]

                        for outcome in outcomes:
                            if outcome in doc_lower:
                                outcome_patterns[outcome] += 1

            # Return outcomes mentioned for multiple drugs
            common_outcomes = [outcome for outcome, count in outcome_patterns.items() if count >= len(drugs) * 0.5]
            return common_outcomes

        except Exception as e:
            self.logger.error(f"Failed to find common outcomes: {e}")
            return []

    async def _find_common_indications(self, drugs: List[str]) -> List[str]:
        """Find common indications across drugs"""
        indication_patterns = defaultdict(int)

        try:
            for drug in drugs:
                results = self.collection.query(
                    query_texts=[f"{drug} indication treatment"],
                    n_results=10,
                    include=["documents"],
                )

                if results["documents"] and results["documents"][0]:
                    for doc in results["documents"][0]:
                        doc_lower = doc.lower()
                        indications = [
                            "diabetes",
                            "heart failure",
                            "chronic kidney disease",
                            "cardiovascular disease",
                            "hypertension",
                        ]

                        for indication in indications:
                            if indication in doc_lower:
                                indication_patterns[indication] += 1

            common_indications = [
                indication for indication, count in indication_patterns.items() if count >= len(drugs) * 0.5
            ]
            return common_indications

        except Exception as e:
            self.logger.error(f"Failed to find common indications: {e}")
            return []

    async def _analyze_indication_patterns(self, entities: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Analyze patterns across indications"""
        insights = []

        try:
            # Analyze heart failure patterns (current focus)
            hf_drugs = []
            for drug in entities.get("drugs", []):
                # Check if drug is used for heart failure
                results = self.collection.query(
                    query_texts=[f"{drug} heart failure"],
                    n_results=5,
                    include=["documents"],
                )

                if results["documents"] and results["documents"][0]:
                    if any("heart failure" in doc.lower() for doc in results["documents"][0]):
                        hf_drugs.append(drug)

            if len(hf_drugs) >= 2:
                insight = {
                    "type": "indication_synergy",
                    "description": f"Multiple drugs show efficacy for heart failure: {', '.join(hf_drugs)}",
                    "confidence": 0.7,
                    "recommendations": [
                        "Compare head-to-head efficacy for heart failure",
                        "Investigate combination therapy potential",
                        "Analyze patient selection criteria for heart failure treatment",
                    ],
                }
                insights.append(insight)

            return insights

        except Exception as e:
            self.logger.error(f"Failed to analyze indication patterns: {e}")
            return insights

    async def _generate_insight_recommendations(self) -> List[str]:
        """Generate actionable recommendations from insights"""
        recommendations = []

        try:
            # Collect recommendations from all insights
            for insight in self.cross_workflow_insights.values():
                recommendations.extend(insight.actionable_recommendations)

            # Add general recommendations based on patterns
            if len(self.temporal_patterns) > 0:
                recommendations.append("Monitor temporal trends for research prioritization")

            if len(self.contradictions) > 0:
                recommendations.append("Resolve contradictory evidence through systematic review")

            if len(self.research_gaps) > 0:
                recommendations.append("Address identified research gaps in future studies")

            # Remove duplicates
            unique_recommendations = list(dict.fromkeys(recommendations))

            return unique_recommendations[:10]  # Top 10 recommendations

        except Exception as e:
            self.logger.error(f"Failed to generate insight recommendations: {e}")
            return recommendations

    def get_enhanced_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics including enhanced features"""
        try:
            # Get base analytics from MVP-1.4
            base_analytics = self.get_document_usage_analytics()

            # Add enhanced analytics
            enhanced_analytics = {
                "base_analytics": base_analytics,
                "temporal_patterns": {
                    "total_patterns": len(self.temporal_patterns),
                    "patterns_by_trend": {
                        trend: len([p for p in self.temporal_patterns.values() if p.trend_direction == trend])
                        for trend in ["increasing", "decreasing", "stable"]
                    },
                    "high_confidence_patterns": len(
                        [p for p in self.temporal_patterns.values() if p.confidence_score > 0.8]
                    ),
                },
                "contradictions": {
                    "total_contradictions": len(self.contradictions),
                    "contradictions_by_severity": {
                        severity: len([c for c in self.contradictions.values() if c.severity == severity])
                        for severity in ["minor", "moderate", "major"]
                    },
                    "entities_with_contradictions": len(set(c.entity for c in self.contradictions.values())),
                },
                "research_gaps": {
                    "total_gaps": len(self.research_gaps),
                    "gaps_by_type": {
                        gap_type: len([g for g in self.research_gaps.values() if g.gap_type == gap_type])
                        for gap_type in [
                            "clinical_trials",
                            "safety_data",
                            "mechanism_studies",
                            "population_studies",
                            "long_term_studies",
                        ]
                    },
                    "high_priority_gaps": len([g for g in self.research_gaps.values() if g.priority_score > 0.8]),
                },
                "cross_workflow_insights": {
                    "total_insights": len(self.cross_workflow_insights),
                    "insights_by_type": {
                        insight_type: len(
                            [i for i in self.cross_workflow_insights.values() if i.insight_type == insight_type]
                        )
                        for insight_type in [
                            "drug_class_pattern",
                            "indication_synergy",
                            "safety_correlation",
                        ]
                    },
                    "high_confidence_insights": len(
                        [i for i in self.cross_workflow_insights.values() if i.confidence_score > 0.8]
                    ),
                },
            }

            return enhanced_analytics

        except Exception as e:
            self.logger.error(f"Failed to get enhanced analytics: {e}")
            return {"error": str(e)}

    async def get_enhanced_research_recommendations(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        ENHANCED: Get comprehensive research recommendations based on similarity search and existing evidence

        This is the FIXED version that performs actual similarity searches to find existing evidence
        for new entities and provides intelligent research strategies.
        """
        self.logger.info("=== ENHANCED RESEARCH RECOMMENDATIONS DEBUG START ===")

        try:
            # Initialize recommendations structure
            recommendations = {
                "research_strategy": "unknown",
                "existing_evidence": {},
                "priority_research": [],
                "gap_addressing": [],
                "contradiction_resolution": [],
                "temporal_insights": [],
                "cross_workflow_opportunities": [],
                "similar_drugs": [],
                "related_documents": 0,
                "confidence_score": 0.0,
            }

            # Extract primary entities for analysis
            primary_drug = entities.get("primary_drug") or entities.get("drug_name")
            primary_disease = entities.get("primary_disease") or entities.get("disease_name")
            drug_class = entities.get("drug_class")

            self.logger.debug(f"Analyzing entities: drug={primary_drug}, disease={primary_disease}, class={drug_class}")

            if not primary_drug:
                self.logger.warning("No primary drug specified - returning generic recommendations")
                recommendations["research_strategy"] = "comprehensive"
                return recommendations

            # STEP 1: Perform similarity search for existing evidence
            existing_evidence_results = await self._find_existing_evidence_for_entity(
                primary_drug, primary_disease, drug_class
            )

            self.logger.debug(f"Existing evidence analysis: {existing_evidence_results}")

            # STEP 2: Determine research strategy based on existing evidence
            strategy_analysis = self._determine_research_strategy(existing_evidence_results, primary_drug, drug_class)

            recommendations.update(
                {
                    "research_strategy": strategy_analysis["strategy"],
                    "existing_evidence": existing_evidence_results.get("evidence_summary", {}),
                    "similar_drugs": existing_evidence_results.get("similar_drugs", []),
                    "related_documents": existing_evidence_results.get("total_documents", 0),
                    "confidence_score": strategy_analysis["confidence"],
                }
            )

            self.logger.info(
                f"Research strategy determined: {strategy_analysis['strategy']} (confidence: {strategy_analysis['confidence']:.2f})"
            )

            # STEP 3: Generate specific recommendations based on strategy
            specific_recommendations = await self._generate_strategy_specific_recommendations(
                strategy_analysis["strategy"],
                primary_drug,
                existing_evidence_results,
            )

            recommendations.update(specific_recommendations)

            # STEP 4: Add existing analysis from enhanced features
            if hasattr(self, "research_gaps") and self.research_gaps:
                # Priority research based on gaps
                high_priority_gaps = [g for g in self.research_gaps.values() if g.priority_score > 0.7]
                for gap in high_priority_gaps[:5]:  # Top 5
                    recommendations["gap_addressing"].extend(gap.suggested_research)

            if hasattr(self, "contradictions") and self.contradictions:
                # Contradiction resolution
                for contradiction in self.contradictions.values():
                    recommendations["contradiction_resolution"].extend(contradiction.resolution_suggestions)

            if hasattr(self, "temporal_patterns") and self.temporal_patterns:
                # Temporal insights
                for pattern in self.temporal_patterns.values():
                    if pattern.confidence_score > 0.7:
                        if pattern.trend_direction == "increasing":
                            recommendations["temporal_insights"].append(
                                f"Capitalize on growing research interest in {pattern.entity}"
                            )
                        elif pattern.trend_direction == "decreasing":
                            recommendations["temporal_insights"].append(
                                f"Investigate reasons for declining research in {pattern.entity}"
                            )

            if hasattr(self, "cross_workflow_insights") and self.cross_workflow_insights:
                # Cross-workflow opportunities
                for insight in self.cross_workflow_insights.values():
                    recommendations["cross_workflow_opportunities"].extend(insight.actionable_recommendations)

            # STEP 5: Compile priority research list
            all_suggestions = []
            for category in [
                "gap_addressing",
                "contradiction_resolution",
                "cross_workflow_opportunities",
            ]:
                all_suggestions.extend(recommendations[category])

            # Add strategy-specific priorities
            all_suggestions.extend(specific_recommendations.get("priority_research", []))

            # Deduplicate and prioritize
            unique_suggestions = list(dict.fromkeys(all_suggestions))
            recommendations["priority_research"] = unique_suggestions[:10]

            self.logger.info("=== ENHANCED RESEARCH RECOMMENDATIONS COMPLETED ===")
            self.logger.info(f"Strategy: {recommendations['research_strategy']}")
            self.logger.info(f"Evidence found: {recommendations['related_documents']} documents")
            self.logger.info(f"Similar drugs: {recommendations['similar_drugs']}")
            self.logger.info(f"Priority recommendations: {len(recommendations['priority_research'])}")

            return recommendations

        except Exception as e:
            self.logger.error(f"Enhanced research recommendations failed: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "research_strategy": "comprehensive",
                "priority_research": [],
                "gap_addressing": [],
                "contradiction_resolution": [],
                "temporal_insights": [],
                "cross_workflow_opportunities": [],
            }

    async def _find_existing_evidence_for_entity(
        self,
        primary_drug: str,
        primary_disease: Optional[str] = None,
        drug_class: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Find existing evidence for an entity using multiple similarity search strategies
        """
        self.logger.debug(f"=== FINDING EXISTING EVIDENCE FOR {primary_drug} ===")

        evidence_results = {
            "total_documents": 0,
            "similar_drugs": [],
            "evidence_summary": {},
            "best_matches": [],
            "search_strategies": {},
        }

        try:
            # Define multiple search strategies with different queries
            search_strategies = [
                {
                    "name": "direct_drug_search",
                    "query": f"{primary_drug}",
                    "weight": 1.0,
                },
                {
                    "name": "drug_class_search",
                    "query": f"{drug_class} {primary_disease}"
                    if drug_class and primary_disease
                    else f"{primary_drug} class",
                    "weight": 0.8,
                },
                {
                    "name": "mechanism_search",
                    "query": f"{primary_drug} mechanism {drug_class}" if drug_class else f"{primary_drug} mechanism",
                    "weight": 0.7,
                },
                {
                    "name": "indication_search",
                    "query": f"{primary_disease} treatment {drug_class}"
                    if primary_disease and drug_class
                    else f"{primary_drug} {primary_disease}"
                    if primary_disease
                    else f"{primary_drug} indication",
                    "weight": 0.6,
                },
            ]

            all_matches = []

            # Execute each search strategy
            for strategy in search_strategies:
                self.logger.debug(f"Executing {strategy['name']}: '{strategy['query']}'")

                try:
                    results = self.collection.query(
                        query_texts=[strategy["query"]],
                        n_results=20,  # Get more results for comprehensive analysis
                        include=["metadatas", "documents", "distances"],
                    )

                    if results["metadatas"] and results["metadatas"][0]:
                        strategy_matches = []

                        for i, (metadata, distance) in enumerate(
                            zip(results["metadatas"][0], results["distances"][0], strict=False)
                        ):
                            # Apply similarity threshold filtering
                            if distance <= self.similarity_thresholds["weak_match"]:  # Only include reasonable matches
                                match_info = {
                                    "metadata": metadata,
                                    "distance": distance,
                                    "strategy": strategy["name"],
                                    "weight": strategy["weight"],
                                    "weighted_score": (1 - distance) * strategy["weight"],  # Higher is better
                                    "document": results["documents"][0][i] if i < len(results["documents"][0]) else "",
                                }
                                strategy_matches.append(match_info)
                                all_matches.append(match_info)

                        evidence_results["search_strategies"][strategy["name"]] = {
                            "matches_found": len(strategy_matches),
                            "best_distance": min([m["distance"] for m in strategy_matches])
                            if strategy_matches
                            else 1.0,
                            "avg_distance": sum([m["distance"] for m in strategy_matches]) / len(strategy_matches)
                            if strategy_matches
                            else 1.0,
                        }

                        self.logger.debug(
                            f"{strategy['name']}: {len(strategy_matches)} matches, best distance: {evidence_results['search_strategies'][strategy['name']]['best_distance']:.3f}"
                        )

                except Exception as e:
                    self.logger.warning(f"Search strategy {strategy['name']} failed: {e}")
                    evidence_results["search_strategies"][strategy["name"]] = {"error": str(e)}

            # Analyze all matches
            if all_matches:
                # Sort by weighted score (best matches first)
                all_matches.sort(key=lambda x: x["weighted_score"], reverse=True)

                evidence_results["total_documents"] = len(all_matches)
                evidence_results["best_matches"] = all_matches[:10]  # Top 10 matches

                # Extract similar drugs from metadata
                similar_drugs = set()
                evidence_by_category = defaultdict(int)

                for match in all_matches:
                    metadata = match["metadata"]
                    distance = match["distance"]

                    # Only consider good matches for drug extraction
                    if distance <= self.similarity_thresholds["good_match"]:
                        # Extract drug names from metadata
                        drug_context = metadata.get("drug_names_context", [])
                        if isinstance(drug_context, str):
                            try:
                                import json

                                drug_context = json.loads(drug_context)
                            except (json.JSONDecodeError, TypeError, ValueError):
                                drug_context = [drug_context]
                        elif not isinstance(drug_context, list):
                            drug_context = []

                        for drug in drug_context:
                            drug_str = str(drug).strip()
                            if drug_str and drug_str.lower() != primary_drug.lower():
                                # Check if it's likely the same drug class for SGLT2 inhibitors
                                if (drug_class and "sglt2" in drug_class.lower() and "flozin" in drug_str.lower()) or (
                                    "flozin" in primary_drug.lower() and "flozin" in drug_str.lower()
                                ):
                                    similar_drugs.add(drug_str)

                    # Categorize evidence types
                    source_type = metadata.get("source_type", "unknown")
                    evidence_by_category[source_type] += 1

                evidence_results["similar_drugs"] = list(similar_drugs)
                evidence_results["evidence_summary"] = dict(evidence_by_category)

                self.logger.debug(
                    f"Analysis complete: {len(all_matches)} total matches, {len(similar_drugs)} similar drugs found"
                )
                self.logger.debug(f"Similar drugs: {list(similar_drugs)}")
                self.logger.debug(f"Evidence summary: {dict(evidence_by_category)}")

            else:
                self.logger.debug("No matches found across all search strategies")

            return evidence_results

        except Exception as e:
            self.logger.error(f"Failed to find existing evidence for {primary_drug}: {e}")
            return evidence_results

    def _determine_research_strategy(
        self,
        evidence_results: Dict[str, Any],
        primary_drug: str,
        drug_class: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Determine the appropriate research strategy based on existing evidence analysis
        """
        self.logger.debug(f"=== DETERMINING RESEARCH STRATEGY FOR {primary_drug} ===")

        total_docs = evidence_results.get("total_documents", 0)
        similar_drugs = evidence_results.get("similar_drugs", [])
        evidence_summary = evidence_results.get("evidence_summary", {})
        search_strategies = evidence_results.get("search_strategies", {})

        self.logger.debug(f"Evidence analysis: {total_docs} docs, {len(similar_drugs)} similar drugs")
        self.logger.debug(f"Evidence by type: {evidence_summary}")

        # Calculate strategy scores
        strategy_scores = {"comprehensive": 0.0, "focused": 0.0, "update": 0.0}

        confidence = 0.5  # Base confidence

        # Factor 1: Total evidence volume
        if total_docs >= 15:
            strategy_scores["update"] += 0.4
            strategy_scores["focused"] += 0.3
            confidence += 0.2
        elif total_docs >= 5:
            strategy_scores["focused"] += 0.4
            strategy_scores["update"] += 0.2
            confidence += 0.1
        else:
            strategy_scores["comprehensive"] += 0.5

        # Factor 2: Similar drugs (drug class evidence)
        if len(similar_drugs) >= 3:
            strategy_scores["update"] += 0.3
            strategy_scores["focused"] += 0.4
            confidence += 0.2
        elif len(similar_drugs) >= 1:
            strategy_scores["focused"] += 0.3
            strategy_scores["update"] += 0.2
            confidence += 0.1
        else:
            strategy_scores["comprehensive"] += 0.3

        # Factor 3: Evidence quality (based on search strategy success)
        best_distances = []
        for strategy_name, strategy_results in search_strategies.items():
            if "best_distance" in strategy_results:
                best_distances.append(strategy_results["best_distance"])

        if best_distances:
            best_overall_distance = min(best_distances)

            if best_overall_distance <= self.similarity_thresholds["excellent_match"]:
                strategy_scores["update"] += 0.3
                confidence += 0.2
            elif best_overall_distance <= self.similarity_thresholds["good_match"]:
                strategy_scores["focused"] += 0.3
                confidence += 0.15
            elif best_overall_distance <= self.similarity_thresholds["moderate_match"]:
                strategy_scores["focused"] += 0.2
                confidence += 0.1
            else:
                strategy_scores["comprehensive"] += 0.2

        # Factor 4: Drug class specific logic
        if drug_class and "sglt2" in drug_class.lower():
            # SGLT2 inhibitors are well-studied class
            if len(similar_drugs) >= 2:  # Other SGLT2s found
                strategy_scores["focused"] += 0.2
                strategy_scores["update"] += 0.1
                confidence += 0.1

        # Factor 5: Evidence diversity
        evidence_types = len(evidence_summary)
        if evidence_types >= 3:
            strategy_scores["update"] += 0.1
            confidence += 0.1
        elif evidence_types >= 2:
            strategy_scores["focused"] += 0.1

        # Determine final strategy
        final_strategy = max(strategy_scores.keys(), key=lambda k: strategy_scores[k])
        final_confidence = min(confidence, 0.95)  # Cap confidence at 95%

        self.logger.debug(f"Strategy scores: {strategy_scores}")
        self.logger.debug(f"Selected strategy: {final_strategy} (confidence: {final_confidence:.2f})")

        return {
            "strategy": final_strategy,
            "confidence": final_confidence,
            "reasoning": {
                "total_documents": total_docs,
                "similar_drugs_count": len(similar_drugs),
                "evidence_types": evidence_types,
                "best_similarity": min(best_distances) if best_distances else 1.0,
                "strategy_scores": strategy_scores,
            },
        }

    async def _generate_strategy_specific_recommendations(
        self, strategy: str, primary_drug: str, evidence_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate specific recommendations based on the determined research strategy
        """
        self.logger.debug(f"=== GENERATING {strategy.upper()} STRATEGY RECOMMENDATIONS FOR {primary_drug} ===")

        recommendations = {
            "priority_research": [],
            "gap_addressing": [],
            "cross_workflow_opportunities": [],
        }

        similar_drugs = evidence_results.get("similar_drugs", [])
        total_docs = evidence_results.get("total_documents", 0)

        try:
            if strategy == "comprehensive":
                # New entity with limited existing evidence
                recommendations["priority_research"] = [
                    f"Conduct comprehensive literature review for {primary_drug}",
                    f"Design Phase II/III clinical trials for {primary_drug}",
                    f"Investigate {primary_drug} mechanism of action",
                    f"Study {primary_drug} safety profile and contraindications",
                    f"Analyze {primary_drug} pharmacokinetics and pharmacodynamics",
                ]

                recommendations["gap_addressing"] = [
                    f"Establish {primary_drug} efficacy baseline",
                    f"Determine optimal {primary_drug} dosing strategies",
                    f"Investigate {primary_drug} drug-drug interactions",
                    f"Study {primary_drug} in diverse patient populations",
                ]

            elif strategy == "focused":
                # Some existing evidence, focus on specific gaps
                recommendations["priority_research"] = [
                    f"Compare {primary_drug} head-to-head with existing alternatives",
                    f"Investigate unique advantages of {primary_drug}",
                    f"Study {primary_drug} in specific patient subgroups",
                    f"Analyze {primary_drug} cost-effectiveness",
                    f"Examine {primary_drug} long-term outcomes",
                ]

                recommendations["gap_addressing"] = [
                    f"Fill evidence gaps specific to {primary_drug}",
                    f"Study {primary_drug} in underrepresented populations",
                    f"Investigate {primary_drug} combination therapies",
                ]

                if similar_drugs:
                    recommendations["cross_workflow_opportunities"] = [
                        f"Leverage insights from {', '.join(similar_drugs[:3])} for {primary_drug} research",
                        f"Design comparative studies: {primary_drug} vs {similar_drugs[0]}" if similar_drugs else "",
                        f"Apply class-wide safety insights to {primary_drug} evaluation",
                    ]
                    recommendations["cross_workflow_opportunities"] = [
                        r for r in recommendations["cross_workflow_opportunities"] if r
                    ]  # Remove empty strings

            elif strategy == "update":
                # Substantial existing evidence, focus on updates and refinements
                recommendations["priority_research"] = [
                    f"Update {primary_drug} evidence synthesis with latest findings",
                    f"Refine {primary_drug} clinical guidelines based on new evidence",
                    f"Investigate emerging {primary_drug} applications",
                    f"Study {primary_drug} real-world effectiveness",
                    f"Analyze {primary_drug} post-market surveillance data",
                ]

                recommendations["gap_addressing"] = [
                    f"Address remaining {primary_drug} knowledge gaps",
                    f"Update {primary_drug} risk-benefit analysis",
                    f"Investigate novel {primary_drug} biomarkers",
                ]

                if similar_drugs:
                    recommendations["cross_workflow_opportunities"] = [
                        f"Conduct network meta-analysis including {primary_drug} and {', '.join(similar_drugs[:3])}",
                        f"Update class-wide recommendations incorporating {primary_drug} evidence",
                        f"Investigate {primary_drug} positioning within therapeutic class",
                        f"Analyze {primary_drug} vs {similar_drugs[0]} in real-world settings" if similar_drugs else "",
                    ]
                    recommendations["cross_workflow_opportunities"] = [
                        r for r in recommendations["cross_workflow_opportunities"] if r
                    ]

            # Add general recommendations based on evidence
            if total_docs > 0:
                recommendations["priority_research"].append(
                    f"Synthesize existing {primary_drug} evidence for clinical decision-making"
                )

            if len(similar_drugs) >= 2:
                recommendations["cross_workflow_opportunities"].append(
                    f"Explore {primary_drug} differentiation within drug class"
                )

            self.logger.debug(f"Generated {len(recommendations['priority_research'])} priority recommendations")
            self.logger.debug(
                f"Generated {len(recommendations['cross_workflow_opportunities'])} cross-workflow opportunities"
            )

            return recommendations

        except Exception as e:
            self.logger.error(f"Failed to generate strategy-specific recommendations: {e}")
            return recommendations
