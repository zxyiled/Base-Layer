import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


class BasePlotter:
    """Helpers shared by every class that draws and saves figures."""

    @staticmethod
    def axis_label(variable, units):
        return f"{variable.replace('_', ' ').capitalize()} ({units[variable]})"

    @staticmethod
    def save_figure(fig, path):
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
