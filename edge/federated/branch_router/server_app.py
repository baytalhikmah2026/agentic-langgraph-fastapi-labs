"""The head office (Lab 94): averages the branches' models round by round (FedAvg)."""

from flwr.app import ArrayRecord, Context
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from branch_router.task import VOCABULARY, initial_weights

app = ServerApp()


@app.main()
def main(grid: Grid, context: Context) -> None:
    strategy = FedAvg(fraction_train=1.0, fraction_evaluate=1.0)  # both branches, every round
    result = strategy.start(
        grid=grid,
        initial_arrays=ArrayRecord(initial_weights()),
        num_rounds=int(context.run_config["num-server-rounds"]),
    )
    w, _ = result.arrays.to_numpy_ndarrays()
    strongest = sorted(zip(w, VOCABULARY, strict=True), reverse=True)[:5]
    print("Words that point most to 'portfolio':", ", ".join(word for _, word in strongest))
