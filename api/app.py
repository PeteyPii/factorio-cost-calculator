import controller
import model
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class ComputeCostsRequest(BaseModel):
    config: model.Configuration
    iterations: int = Field(default=100, ge=1, le=1000)


class ComputeCostsResponse(BaseModel):
    costs: list[controller.ItemCost]


@app.post("/compute_costs")
async def compute_costs(request: ComputeCostsRequest) -> ComputeCostsResponse:
    c = controller.Controller(request.config)
    return ComputeCostsResponse(costs=c.compute_all_costs(request.iterations))
