from enum import Enum


class IndexType(Enum):
    PARAGRAPH_INDEX = "text_model"
    QA_INDEX = "qa_model"
    PARENT_CHILD_INDEX = "hierarchical_model"
    SUMMARY_INDEX = "summary_index"
