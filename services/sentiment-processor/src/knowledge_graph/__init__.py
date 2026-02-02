"""Knowledge Graph for financial sentiment analysis.

This module extracts entities and relationships from financial texts
to build a graph database using NetworkX for local analysis.

Uses:
- spaCy for Named Entity Recognition (NER)
- Dependency parsing for relation extraction
- NetworkX for graph construction and analytics
- Firestore for persistent storage

Features:
- Financial entity recognition (Fed, Gold, Dollar, etc.)
- Relation extraction (CAUSED_BY, IMPACTS, CORRELATED_WITH)
- Graph analytics (PageRank, community detection)
- Sentiment propagation through the graph
- Incremental graph updates

Cost: $0 (uses open-source spaCy + NetworkX)
"""

import asyncio
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Optional ML deps (Poetry group: `ml`)
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
from google.cloud import firestore
from google.api_core.exceptions import NotFound

# Try to import spaCy
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from spacy.tokens import Doc
    SPACY_TOKENS_AVAILABLE = True
except ImportError:
    SPACY_TOKENS_AVAILABLE = False

from sentilyze_core import get_logger, get_settings
from sentilyze_core.exceptions import ExternalServiceError

logger = get_logger(__name__)
settings = get_settings()


class EntityType(Enum):
    """Financial entity types."""
    ORGANIZATION = "ORG"
    PERSON = "PERSON"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"
    ECONOMIC_INDICATOR = "ECONOMIC_INDICATOR"
    FINANCIAL_INSTRUMENT = "FINANCIAL_INSTRUMENT"
    EVENT = "EVENT"
    LOCATION = "GPE"
    UNKNOWN = "UNKNOWN"


class RelationType(Enum):
    """Types of relationships between entities."""
    CAUSED_BY = "caused_by"
    NEGATIVELY_IMPACTS = "negatively_impacts"
    POSITIVELY_IMPACTS = "positively_impacts"
    CORRELATED_WITH = "correlated_with"
    INVERSELY_CORRELATED = "inversely_correlated"
    MENTIONS = "mentions"
    PART_OF = "part_of"
    OPERATES_IN = "operates_in"
    REGULATES = "regulates"


@dataclass
class FinancialEntity:
    """Financial entity extracted from text."""
    id: str
    name: str
    entity_type: EntityType
    aliases: list[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    mention_count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "aliases": self.aliases,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "mention_count": self.mention_count,
            "metadata": self.metadata,
        }


@dataclass
class EntityRelation:
    """Relationship between two entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    weight: float = 1.0
    sentiment: float = 0.0  # -1 to 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "weight": self.weight,
            "sentiment": self.sentiment,
        }


@dataclass
class ExtractedText:
    """Text with extracted entities and relations."""
    text_id: str
    text: str
    timestamp: datetime
    entities: list[FinancialEntity] = field(default_factory=list)
    relations: list[EntityRelation] = field(default_factory=list)
    overall_sentiment: float = 0.0


class FinancialEntityExtractor:
    """Extract financial entities from text using spaCy.
    
    Uses spaCy's NER with custom patterns for financial domain:
    - Fed, ECB, BOJ (central banks)
    - Gold, Silver, Oil (commodities)
    - USD, EUR, BTC (currencies)
    - CPI, GDP, Interest Rates (economic indicators)
    """
    
    # Financial entity patterns (in addition to spaCy NER)
    FINANCIAL_PATTERNS = {
        EntityType.COMMODITY: [
            "gold", "silver", "oil", "crude", "brent", "copper", "platinum",
            "palladium", "natural gas", "wheat", "corn", "soybean", "coffee",
        ],
        EntityType.CURRENCY: [
            "usd", "dollar", "eur", "euro", "gbp", "pound", "jpy", "yen",
            "cny", "yuan", "btc", "bitcoin", "eth", "ethereum", "crypto",
            "cryptocurrency",
        ],
        EntityType.ECONOMIC_INDICATOR: [
            "cpi", "inflation", "gdp", "unemployment", "nfp", "jobs report",
            "interest rate", "fed funds rate", "treasury yield", "bond yield",
        ],
        EntityType.ORGANIZATION: [
            "fed", "federal reserve", "ecb", "european central bank",
            "boj", "bank of japan", "imf", "world bank", "bis",
            "sec", "cftc", "treasury",
        ],
        EntityType.FINANCIAL_INSTRUMENT: [
            "s&p 500", "spx", "nasdaq", "dow", "dow jones", "ftse",
            "dax", "nikkei", "vix", "futures", "options", "etf",
        ],
    }
    
    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self.model_name = model_name
        self._nlp: Optional[Any] = None
        self._entity_map: dict[str, FinancialEntity] = {}
        
    @property
    def nlp(self) -> Any:
        """Get or load spaCy model."""
        if self._nlp is None:
            if not SPACY_AVAILABLE:
                raise ExternalServiceError(
                    "spaCy not available. Install with: pip install spacy",
                    service="entity_extractor"
                )
            try:
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Loaded spaCy model: {self.model_name}")
            except OSError:
                logger.warning(f"spaCy model {self.model_name} not found. Using blank model.")
                self._nlp = spacy.blank("en")
        return self._nlp
    
    def extract_entities(self, text: str) -> list[FinancialEntity]:
        """Extract financial entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted entities
        """
        if not text or not SPACY_AVAILABLE:
            return []
        
        doc = self.nlp(text)
        entities = []
        
        # Extract spaCy entities
        for ent in doc.ents:
            entity_type = self._map_spacy_entity_type(ent.label_)
            entity_id = self._generate_entity_id(ent.text, entity_type)
            
            entity = FinancialEntity(
                id=entity_id,
                name=ent.text,
                entity_type=entity_type,
                aliases=[ent.text.lower()],
                metadata={
                    "spacy_label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                }
            )
            entities.append(entity)
        
        # Extract pattern-based financial entities
        text_lower = text.lower()
        for entity_type, patterns in self.FINANCIAL_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Check if already extracted by spaCy
                    already_extracted = any(
                        e.entity_type == entity_type and pattern in e.name.lower()
                        for e in entities
                    )
                    if not already_extracted:
                        entity_id = self._generate_entity_id(pattern, entity_type)
                        entity = FinancialEntity(
                            id=entity_id,
                            name=pattern.title(),
                            entity_type=entity_type,
                            aliases=[pattern],
                            metadata={"source": "pattern_matching"}
                        )
                        entities.append(entity)
        
        return entities
    
    def _map_spacy_entity_type(self, spacy_label: str) -> EntityType:
        """Map spaCy entity labels to financial entity types."""
        mapping = {
            "ORG": EntityType.ORGANIZATION,
            "PERSON": EntityType.PERSON,
            "GPE": EntityType.LOCATION,
            "PRODUCT": EntityType.FINANCIAL_INSTRUMENT,
            "MONEY": EntityType.CURRENCY,
        }
        return mapping.get(spacy_label, EntityType.UNKNOWN)
    
    def _generate_entity_id(self, name: str, entity_type: EntityType) -> str:
        """Generate unique ID for entity."""
        key = f"{entity_type.value}:{name.lower()}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


class RelationExtractor:
    """Extract relationships between entities using dependency parsing.
    
    Uses spaCy's dependency parser to identify:
    - Causal relationships ("X caused Y")
    - Impact relationships ("X impacts Y")
    - Correlations ("X and Y moved together")
    """
    
    # Causal/impact keywords
    CAUSAL_INDICATORS = ["cause", "lead", "result", "trigger", "due to", "because"]
    IMPACT_INDICATORS = ["impact", "affect", "influence", "drive", "push", "boost"]
    NEGATIVE_INDICATORS = ["drop", "fall", "crash", "plunge", "decline", "decrease"]
    POSITIVE_INDICATORS = ["rise", "increase", "surge", "jump", "soar", "gain"]
    
    def __init__(self, entity_extractor: FinancialEntityExtractor) -> None:
        self.entity_extractor = entity_extractor
        
    def extract_relations(
        self,
        text: str,
        entities: list[FinancialEntity],
    ) -> list[EntityRelation]:
        """Extract relationships between entities.
        
        Args:
            text: Input text
            entities: Extracted entities
            
        Returns:
            List of entity relations
        """
        if not entities or len(entities) < 2:
            return []
        
        relations = []
        text_lower = text.lower()
        
        # Look for entity pairs with causal/impact indicators
        for i, source in enumerate(entities):
            for target in entities[i+1:]:
                relation = self._detect_relation(source, target, text_lower)
                if relation:
                    relations.append(relation)
        
        return relations
    
    def _detect_relation(
        self,
        source: FinancialEntity,
        target: FinancialEntity,
        text_lower: str,
    ) -> Optional[EntityRelation]:
        """Detect relation type between two entities."""
        # Check for causal indicators
        for indicator in self.CAUSAL_INDICATORS:
            if indicator in text_lower:
                return EntityRelation(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=RelationType.CAUSED_BY,
                    confidence=0.7,
                    evidence=[indicator],
                )
        
        # Check for impact indicators
        for indicator in self.IMPACT_INDICATORS:
            if indicator in text_lower:
                # Determine direction (positive/negative)
                sentiment = self._detect_sentiment_direction(text_lower)
                
                relation_type = (
                    RelationType.POSITIVELY_IMPACTS if sentiment > 0
                    else RelationType.NEGATIVELY_IMPACTS
                )
                
                return EntityRelation(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=relation_type,
                    confidence=0.6,
                    evidence=[indicator],
                    sentiment=sentiment,
                )
        
        # Default: mention relation
        return EntityRelation(
            source_id=source.id,
            target_id=target.id,
            relation_type=RelationType.MENTIONS,
            confidence=0.3,
        )
    
    def _detect_sentiment_direction(self, text_lower: str) -> float:
        """Detect positive/negative sentiment in text."""
        pos_count = sum(1 for word in self.POSITIVE_INDICATORS if word in text_lower)
        neg_count = sum(1 for word in self.NEGATIVE_INDICATORS if word in text_lower)
        
        if pos_count > neg_count:
            return 1.0
        elif neg_count > pos_count:
            return -1.0
        return 0.0


class KnowledgeGraphBuilder:
    """Build and manage knowledge graph using NetworkX.
    
    Stores graph in NetworkX with:
    - Nodes: Financial entities
    - Edges: Relationships with weights and sentiment
    
    Persists to Firestore for durability.
    """
    
    def __init__(
        self,
        firestore_client: Optional[firestore.Client] = None,
        collection: str = "knowledge_graph",
    ) -> None:
        if not NETWORKX_AVAILABLE:
            raise ExternalServiceError(
                "networkx not available. Install with: `poetry install --with ml`",
                service="knowledge_graph",
            )
        if not NUMPY_AVAILABLE:
            raise ExternalServiceError(
                "numpy not available. Install with: `poetry install --with ml`",
                service="knowledge_graph",
            )
        self.project_id = settings.google_cloud_project
        self._firestore_client = firestore_client
        self._collection = collection
        
        # Initialize graph
        self.graph = nx.DiGraph()
        
        # Entity extractor
        self.entity_extractor = FinancialEntityExtractor()
        self.relation_extractor = RelationExtractor(self.entity_extractor)
        
        # Tracking
        self._entity_map: dict[str, FinancialEntity] = {}
        self._initialized = False
        
    @property
    def firestore_client(self) -> firestore.Client:
        """Get or create Firestore client."""
        if self._firestore_client is None:
            self._firestore_client = firestore.Client(project=self.project_id)
        return self._firestore_client
    
    async def initialize(self) -> None:
        """Initialize knowledge graph from Firestore."""
        if self._initialized:
            return
        
        try:
            await self._load_from_firestore()
            self._initialized = True
            logger.info(
                f"Knowledge graph initialized",
                nodes=self.graph.number_of_nodes(),
                edges=self.graph.number_of_edges(),
            )
        except Exception as e:
            logger.error(f"Failed to initialize knowledge graph: {e}")
            raise
    
    async def process_text(
        self,
        text: str,
        text_id: Optional[str] = None,
        sentiment: float = 0.0,
    ) -> ExtractedText:
        """Process text and update knowledge graph.
        
        Args:
            text: Input text
            text_id: Optional text identifier (generated if not provided)
            sentiment: Overall sentiment score (-1 to 1)
            
        Returns:
            ExtractedText with entities and relations
        """
        if not text_id:
            text_id = hashlib.md5(text.encode()).hexdigest()[:16]
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(text)
        
        # Extract relations
        relations = self.relation_extractor.extract_relations(text, entities)
        
        # Create extracted text
        extracted = ExtractedText(
            text_id=text_id,
            text=text,
            timestamp=datetime.utcnow(),
            entities=entities,
            relations=relations,
            overall_sentiment=sentiment,
        )
        
        # Update graph
        await self._update_graph(extracted)
        
        # Persist to Firestore
        await self._persist_text(extracted)
        
        return extracted
    
    async def _update_graph(self, extracted: ExtractedText) -> None:
        """Update graph with extracted entities and relations."""
        # Add/update nodes (entities)
        for entity in extracted.entities:
            if entity.id in self._entity_map:
                # Update existing entity
                existing = self._entity_map[entity.id]
                existing.mention_count += 1
                existing.last_seen = datetime.utcnow()
                existing.aliases = list(set(existing.aliases + entity.aliases))
            else:
                # New entity
                self._entity_map[entity.id] = entity
            
            # Add to NetworkX graph
            self.graph.add_node(
                entity.id,
                name=entity.name,
                type=entity.entity_type.value,
                mention_count=self._entity_map[entity.id].mention_count,
            )
        
        # Add edges (relations)
        for relation in extracted.relations:
            if self.graph.has_edge(relation.source_id, relation.target_id):
                # Update existing edge
                edge_data = self.graph[relation.source_id][relation.target_id]
                edge_data["weight"] += relation.weight
                edge_data["mention_count"] = edge_data.get("mention_count", 1) + 1
            else:
                # New edge
                self.graph.add_edge(
                    relation.source_id,
                    relation.target_id,
                    relation_type=relation.relation_type.value,
                    weight=relation.weight,
                    sentiment=relation.sentiment,
                    mention_count=1,
                )
    
    async def _persist_text(self, extracted: ExtractedText) -> None:
        """Persist extracted text to Firestore."""
        try:
            doc_ref = self.firestore_client.collection(self._collection).document(
                f"text_{extracted.text_id}"
            )
            
            data = {
                "text_id": extracted.text_id,
                "text_preview": extracted.text[:200],
                "timestamp": extracted.timestamp,
                "entity_ids": [e.id for e in extracted.entities],
                "relations": [r.to_dict() for r in extracted.relations],
                "overall_sentiment": extracted.overall_sentiment,
            }
            
            await asyncio.to_thread(doc_ref.set, data)
            
            # Persist entities
            for entity in extracted.entities:
                entity_ref = self.firestore_client.collection(
                    f"{self._collection}_entities"
                ).document(entity.id)
                await asyncio.to_thread(entity_ref.set, entity.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to persist text: {e}")
    
    async def _load_from_firestore(self) -> None:
        """Load graph from Firestore."""
        try:
            # Load entities
            entities_ref = self.firestore_client.collection(f"{self._collection}_entities")
            docs = await asyncio.to_thread(entities_ref.limit(10000).stream)
            
            count = 0
            async for doc in docs:
                data = doc.to_dict()
                entity = FinancialEntity(
                    id=data["id"],
                    name=data["name"],
                    entity_type=EntityType(data["entity_type"]),
                    aliases=data.get("aliases", []),
                    mention_count=data.get("mention_count", 1),
                    metadata=data.get("metadata", {}),
                )
                self._entity_map[entity.id] = entity
                self.graph.add_node(
                    entity.id,
                    name=entity.name,
                    type=entity.entity_type.value,
                    mention_count=entity.mention_count,
                )
                count += 1
            
            logger.info(f"Loaded {count} entities from Firestore")
            
        except Exception as e:
            logger.error(f"Failed to load from Firestore: {e}")
    
    def get_entity_centrality(self, top_n: int = 10) -> list[tuple[str, float]]:
        """Get most central entities using PageRank.
        
        Args:
            top_n: Number of top entities to return
            
        Returns:
            List of (entity_id, score) tuples
        """
        if self.graph.number_of_nodes() == 0:
            return []
        
        try:
            pagerank = nx.pagerank(self.graph, weight="weight")
            sorted_entities = sorted(
                pagerank.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_entities[:top_n]
        except Exception as e:
            logger.error(f"PageRank calculation failed: {e}")
            return []
    
    def detect_communities(self) -> dict[str, int]:
        """Detect entity communities using Louvain algorithm.
        
        Returns:
            Dictionary mapping entity_id to community_id
        """
        if self.graph.number_of_nodes() == 0:
            return {}
        
        try:
            # Convert to undirected for community detection
            undirected = self.graph.to_undirected()
            communities = nx.community.louvain_communities(undirected)
            
            # Map entities to community IDs
            community_map = {}
            for i, community in enumerate(communities):
                for entity_id in community:
                    community_map[entity_id] = i
            
            return community_map
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {}
    
    def find_shortest_path(
        self,
        entity_a: str,
        entity_b: str,
    ) -> Optional[list[str]]:
        """Find shortest path between two entities.
        
        Args:
            entity_a: Source entity name or ID
            entity_b: Target entity name or ID
            
        Returns:
            List of entity IDs in path, or None if no path
        """
        # Resolve entity names to IDs
        id_a = self._resolve_entity_id(entity_a)
        id_b = self._resolve_entity_id(entity_b)
        
        if not id_a or not id_b:
            return None
        
        try:
            path = nx.shortest_path(self.graph, id_a, id_b)
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return None
    
    def propagate_sentiment(self, seed_entity: str, sentiment: float) -> dict[str, float]:
        """Propagate sentiment from seed entity through graph.
        
        Uses random walk with restarts to propagate sentiment.
        
        Args:
            seed_entity: Starting entity name or ID
            sentiment: Sentiment score (-1 to 1)
            
        Returns:
            Dictionary mapping entity_id to propagated sentiment
        """
        seed_id = self._resolve_entity_id(seed_entity)
        if not seed_id:
            return {}
        
        try:
            # Personalized PageRank from seed
            personalization = {node: 0.0 for node in self.graph.nodes()}
            personalization[seed_id] = 1.0
            
            pagerank = nx.pagerank(
                self.graph,
                personalization=personalization,
                weight="weight"
            )
            
            # Scale by input sentiment
            propagated = {
                node: score * sentiment
                for node, score in pagerank.items()
            }
            
            return propagated
        except Exception as e:
            logger.error(f"Sentiment propagation failed: {e}")
            return {}
    
    def _resolve_entity_id(self, name_or_id: str) -> Optional[str]:
        """Resolve entity name to ID."""
        # Check if it's already an ID
        if name_or_id in self._entity_map:
            return name_or_id
        
        # Search by name
        name_lower = name_or_id.lower()
        for entity_id, entity in self._entity_map.items():
            if entity.name.lower() == name_lower or name_lower in entity.aliases:
                return entity_id
        
        return None
    
    def get_related_entities(
        self,
        entity_name: str,
        relation_type: Optional[RelationType] = None,
    ) -> list[FinancialEntity]:
        """Get entities related to given entity.
        
        Args:
            entity_name: Entity name or ID
            relation_type: Optional relation type filter
            
        Returns:
            List of related entities
        """
        entity_id = self._resolve_entity_id(entity_name)
        if not entity_id:
            return []
        
        related = []
        
        # Get neighbors
        if entity_id in self.graph:
            for neighbor_id in self.graph.successors(entity_id):
                if relation_type:
                    edge_data = self.graph[entity_id][neighbor_id]
                    if edge_data.get("relation_type") != relation_type.value:
                        continue
                
                if neighbor_id in self._entity_map:
                    related.append(self._entity_map[neighbor_id])
        
        return related
    
    def export_graph(self, format: str = "json") -> dict[str, Any]:
        """Export graph to various formats.
        
        Args:
            format: Export format (json, graphml, gexf)
            
        Returns:
            Graph data in specified format
        """
        if format == "json":
            return {
                "nodes": [
                    {
                        "id": node,
                        **self.graph.nodes[node]
                    }
                    for node in self.graph.nodes()
                ],
                "edges": [
                    {
                        "source": u,
                        "target": v,
                        **data
                    }
                    for u, v, data in self.graph.edges(data=True)
                ],
                "stats": {
                    "node_count": self.graph.number_of_nodes(),
                    "edge_count": self.graph.number_of_edges(),
                    "density": nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0,
                }
            }
        elif format == "graphml":
            # Return as string
            import io
            buffer = io.StringIO()
            nx.write_graphml(self.graph, buffer)
            return {"graphml": buffer.getvalue()}
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def close(self) -> None:
        """Close knowledge graph."""
        logger.info(
            f"Knowledge graph closed",
            nodes=self.graph.number_of_nodes(),
            edges=self.graph.number_of_edges(),
        )


# Global instance for dependency injection
_knowledge_graph_instance: Optional[KnowledgeGraphBuilder] = None


async def get_knowledge_graph(
    firestore_client: Optional[firestore.Client] = None,
) -> KnowledgeGraphBuilder:
    """Get or create knowledge graph instance (FastAPI dependency)."""
    global _knowledge_graph_instance
    
    if _knowledge_graph_instance is None:
        _knowledge_graph_instance = KnowledgeGraphBuilder(
            firestore_client=firestore_client
        )
        await _knowledge_graph_instance.initialize()
    
    return _knowledge_graph_instance


async def close_knowledge_graph() -> None:
    """Close global knowledge graph instance."""
    global _knowledge_graph_instance
    if _knowledge_graph_instance:
        await _knowledge_graph_instance.close()
        _knowledge_graph_instance = None
