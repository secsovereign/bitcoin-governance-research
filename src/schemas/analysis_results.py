"""JSON schemas for analysis result validation."""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path

# Base schema structure
BASE_SCHEMA = {
    "type": "object",
    "required": ["metadata", "data"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["analysis_name", "timestamp", "version"],
            "properties": {
                "analysis_name": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "version": {"type": "string"},
                "data_sources": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "parameters": {"type": "object"}
            }
        },
        "data": {"type": "object"}
    }
}

# Power concentration schema
POWER_CONCENTRATION_SCHEMA = {
    **BASE_SCHEMA,
    "properties": {
        **BASE_SCHEMA["properties"],
        "data": {
            "type": "object",
            "required": ["concentration_metrics", "maintainer_stats"],
            "properties": {
                "concentration_metrics": {
                    "type": "object",
                    "required": ["gini_coefficient", "top_n_shares", "hhi"],
                    "properties": {
                        "gini_coefficient": {"type": "number", "minimum": 0, "maximum": 1},
                        "top_n_shares": {
                            "type": "object",
                            "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "hhi": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                },
                "maintainer_stats": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["unified_id", "merge_count", "review_count"],
                        "properties": {
                            "unified_id": {"type": "string"},
                            "merge_count": {"type": "integer", "minimum": 0},
                            "review_count": {"type": "integer", "minimum": 0},
                            "centrality_scores": {"type": "object"}
                        }
                    }
                }
            }
        }
    }
}

# Maintainer premium schema
MAINTAINER_PREMIUM_SCHEMA = {
    **BASE_SCHEMA,
    "properties": {
        **BASE_SCHEMA["properties"],
        "data": {
            "type": "object",
            "required": ["statistical_results", "effect_sizes"],
            "properties": {
                "statistical_results": {
                    "type": "object",
                    "properties": {
                        "chi_square": {
                            "type": "object",
                            "properties": {
                                "statistic": {"type": "number"},
                                "p_value": {"type": "number", "minimum": 0, "maximum": 1},
                                "degrees_of_freedom": {"type": "integer"}
                            }
                        },
                        "t_test": {
                            "type": "object",
                            "properties": {
                                "statistic": {"type": "number"},
                                "p_value": {"type": "number", "minimum": 0, "maximum": 1},
                                "effect_size": {"type": "number"}
                            }
                        },
                        "logistic_regression": {
                            "type": "object",
                            "properties": {
                                "coefficients": {"type": "object"},
                                "p_values": {"type": "object"},
                                "odds_ratios": {"type": "object"}
                            }
                        }
                    }
                },
                "effect_sizes": {
                    "type": "object",
                    "properties": {
                        "cohens_d": {"type": "number"},
                        "odds_ratio": {"type": "number", "minimum": 0},
                        "confidence_interval": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        }
                    }
                }
            }
        }
    }
}

# Decision criteria schema
DECISION_CRITERIA_SCHEMA = {
    **BASE_SCHEMA,
    "properties": {
        **BASE_SCHEMA["properties"],
        "data": {
            "type": "object",
            "required": ["rejection_reasons", "criteria_consistency"],
            "properties": {
                "rejection_reasons": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["reason", "count", "percentage"],
                        "properties": {
                            "reason": {"type": "string"},
                            "count": {"type": "integer", "minimum": 0},
                            "percentage": {"type": "number", "minimum": 0, "maximum": 100}
                        }
                    }
                },
                "criteria_consistency": {
                    "type": "object",
                    "properties": {
                        "consistency_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "documented_criteria_count": {"type": "integer"},
                        "implicit_criteria_count": {"type": "integer"}
                    }
                }
            }
        }
    }
}


def validate_result(result: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate analysis result against schema.
    
    Args:
        result: Analysis result dictionary
        schema: JSON schema to validate against
    
    Returns:
        (is_valid, error_message)
    """
    # Simple validation - in production, use jsonschema library
    try:
        # Check required fields
        if "metadata" not in result:
            return False, "Missing 'metadata' field"
        
        if "data" not in result:
            return False, "Missing 'data' field"
        
        metadata = result["metadata"]
        required_meta = schema["properties"]["metadata"]["required"]
        for field in required_meta:
            if field not in metadata:
                return False, f"Missing required metadata field: {field}"
        
        # Check data structure based on schema
        data = result["data"]
        required_data = schema["properties"]["data"].get("required", [])
        for field in required_data:
            if field not in data:
                return False, f"Missing required data field: {field}"
        
        return True, None
    
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def create_result_template(analysis_name: str, version: str = "1.0.0") -> Dict[str, Any]:
    """Create a template result structure."""
    return {
        "metadata": {
            "analysis_name": analysis_name,
            "timestamp": None,  # Should be set when saving
            "version": version,
            "data_sources": [],
            "parameters": {}
        },
        "data": {}
    }

