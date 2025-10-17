# Copyright (C) 2025 Bunting Labs, Inc.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Graph node types"""
    LOCATION = "Location"
    ADMINISTRATIVE_UNIT = "AdministrativeUnit" 
    FEATURE = "Feature"
    DATASET = "Dataset"
    ATTRIBUTE = "Attribute"
    TIME_PERIOD = "TimePeriod"
    CONCEPT = "Concept"
    USER_QUERY = "UserQuery"


class RelationshipType(str, Enum):
    """Graph relationship types"""
    CONTAINS = "CONTAINS"
    ADJACENT_TO = "ADJACENT_TO"
    PART_OF = "PART_OF"
    HAS_ATTRIBUTE = "HAS_ATTRIBUTE"
    OCCURS_DURING = "OCCURS_DURING"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    RELATED_TO = "RELATED_TO"
    QUERIES = "QUERIES"
    MENTIONS = "MENTIONS"


class GraphNode(BaseModel):
    """Base graph node model"""
    id: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class LocationNode(GraphNode):
    """Geographic location node"""
    name: str
    geometry_type: Optional[str] = None
    coordinates: Optional[List[float]] = None
    bbox: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    admin_level: Optional[int] = None
    country_code: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.LOCATION]


class AdministrativeUnitNode(GraphNode):
    """Administrative unit node (country, state, city, etc.)"""
    name: str
    admin_level: int  # 0=country, 1=state, 2=county, etc.
    iso_code: Optional[str] = None
    geometry_type: Optional[str] = None
    coordinates: Optional[List[float]] = None
    bbox: Optional[List[float]] = None
    population: Optional[int] = None
    area_sq_km: Optional[float] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.ADMINISTRATIVE_UNIT]


class FeatureNode(GraphNode):
    """GIS feature/layer node"""
    name: str
    feature_type: str  # point, line, polygon, etc.
    dataset_id: Optional[str] = None
    geometry_type: Optional[str] = None
    coordinates: Optional[List[float]] = None
    bbox: Optional[List[float]] = None
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.FEATURE]


class DatasetNode(GraphNode):
    """Dataset/layer metadata node"""
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    data_type: Optional[str] = None  # vector, raster, etc.
    crs: Optional[str] = None
    bbox: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.DATASET]


class AttributeNode(GraphNode):
    """Attribute/field metadata node"""
    name: str
    data_type: str
    description: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unique_values: Optional[List[str]] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.ATTRIBUTE]


class TimePeriodNode(GraphNode):
    """Temporal period node"""
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    granularity: Optional[str] = None  # year, month, day, etc.
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.TIME_PERIOD]


class ConceptNode(GraphNode):
    """Abstract concept node"""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    synonyms: Optional[List[str]] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.CONCEPT]


class UserQueryNode(GraphNode):
    """User query node for query understanding"""
    query_text: str
    intent: Optional[str] = None
    entities: Optional[List[str]] = Field(default_factory=list)
    spatial_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    temporal_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.labels = [NodeType.USER_QUERY]


class GraphRelationship(BaseModel):
    """Graph relationship model"""
    type: RelationshipType
    start_node: str  # Node ID
    end_node: str    # Node ID
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"


class SpatialRelationship(GraphRelationship):
    """Spatial relationship with distance/direction info"""
    distance_km: Optional[float] = None
    direction: Optional[str] = None  # north, south, east, west, etc.
    
    def __init__(self, **data):
        super().__init__(**data)
        if 'distance_km' in data:
            self.properties['distance_km'] = data['distance_km']
        if 'direction' in data:
            self.properties['direction'] = data['direction']


class TemporalRelationship(GraphRelationship):
    """Temporal relationship with time info"""
    duration_days: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if 'duration_days' in data:
            self.properties['duration_days'] = data['duration_days']


# Graph query and response models
class GraphQuery(BaseModel):
    """Graph database query"""
    cypher: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GraphQueryResult(BaseModel):
    """Graph query result"""
    records: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None
    
    
class CreateNodeRequest(BaseModel):
    """Request to create a new node"""
    node_type: NodeType
    properties: Dict[str, Any]
    

class CreateRelationshipRequest(BaseModel):
    """Request to create a new relationship"""
    start_node_id: str
    end_node_id: str
    relationship_type: RelationshipType
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)