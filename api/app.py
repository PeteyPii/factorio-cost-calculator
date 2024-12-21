import controller
import model
import simplejson
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtendedJSONResponse(JSONResponse):
    def render(self, content):
        return simplejson.dumps(
            content,
            ignore_nan=True,
            ensure_ascii=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class ComputeCostsRequest(BaseModel):
    config: model.Configuration
    iterations: int = Field(default=100, ge=1, le=1000)


class ComputeCostsResponse(BaseModel):
    costs: list[controller.ItemCost]


@app.post("/compute_costs", response_class=ExtendedJSONResponse)
def compute_costs(request: ComputeCostsRequest) -> ComputeCostsResponse:
    c = controller.Controller(request.config)
    return ComputeCostsResponse(costs=c.compute_all_costs(request.iterations))


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
