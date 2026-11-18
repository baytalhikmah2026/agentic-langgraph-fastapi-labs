"""A branch (Lab 94): trains on its own questions and sends back only the model's numbers."""

from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from branch_router.task import accuracy, branch_data, train

app = ClientApp()


@app.train()
def train_on_branch(msg: Message, context: Context) -> Message:
    weights = msg.content["arrays"].to_numpy_ndarrays()
    x, y = branch_data(int(context.node_config["partition-id"]))
    weights = train(
        weights,
        x,
        y,
        epochs=int(context.run_config["local-epochs"]),
        lr=float(context.run_config["learning-rate"]),
    )
    metrics = {"num-examples": len(y), "train-accuracy": accuracy(weights, x, y)}
    content = RecordDict({"arrays": ArrayRecord(weights), "metrics": MetricRecord(metrics)})
    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate_on_branch(msg: Message, context: Context) -> Message:
    weights = msg.content["arrays"].to_numpy_ndarrays()
    x, y = branch_data(int(context.node_config["partition-id"]))
    metrics = {"num-examples": len(y), "eval-accuracy": accuracy(weights, x, y)}
    return Message(content=RecordDict({"metrics": MetricRecord(metrics)}), reply_to=msg)
