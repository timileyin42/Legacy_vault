from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    title: str
    detail: str
    priority: str
    action: str


class RecommendationsResponse(BaseModel):
    completion_percent: int
    items: list[RecommendationItem]


class RiskInsight(BaseModel):
    label: str
    level: str
    score: int


class RiskAnalysisResponse(BaseModel):
    insights: list[RiskInsight]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[str]
