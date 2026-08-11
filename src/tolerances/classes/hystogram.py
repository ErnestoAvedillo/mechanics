from matplotlib import pyplot as plt
import base64
import io
from tolerances.pymodels.dimension import Dimension


class Hystogram:
    def __init__(self, dimension: Dimension, bins: int = 50, xlabel: str = "Value", ylabel: str = "Density", title: str = "Hystogram"):
        self.dimension = dimension
        self.data = dimension.vector_samples
        self.bins = bins
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.hyst_plot = None
        self.hyst_axes = None

    def plot(self):
        self.hyst_plot = plt.figure(figsize=(12, 6))
        self.hyst_axes = self.hyst_plot.add_subplot(111)
        _, bin_edges, patches = self.hyst_axes.hist(
            self.data,
            bins=self.bins,
            density=True,
            alpha=0.75,
            edgecolor='black',
        )

        # Column color by sign: negative red, positive green.
        for i, patch in enumerate(patches):
            bin_center = (bin_edges[i] + bin_edges[i + 1]) / 2
            if bin_center < 0:
                patch.set_facecolor('#d9534f')
            elif bin_center > 0:
                patch.set_facecolor('#5cb85c')
            else:
                patch.set_facecolor('#9ea7b3')
        
        # Vertical line for the mean
        if self.dimension.mean is not None:
            mean_value = self.dimension.mean.magnitude
            self.hyst_axes.axvline(mean_value, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_value:.4f}')

        if self.dimension.sigma and self.dimension.CP is not None:
            Upper_Limit = self.dimension.mean.magnitude + self.dimension.sigma.magnitude * 4
            self.hyst_axes.axvline(Upper_Limit, color='blue', linestyle='-.', linewidth=2, label=f'USL: {Upper_Limit:.4f}')
            Lower_Limit = self.dimension.mean.magnitude - self.dimension.sigma.magnitude * 4
            self.hyst_axes.axvline(Lower_Limit, color='purple', linestyle='-.', linewidth=2, label=f'LSL: {Lower_Limit:.4f}')

        # Vertical line for the nominal
        nominal_value = self.dimension.nominal.magnitude if self.dimension.nominal is not None else None
        if nominal_value is not None:
            self.hyst_axes.axvline(nominal_value, color='green', linestyle=':', linewidth=2, label=f'Nominal: {nominal_value:.4f}')

        # Vertical line for the upper tolerance
        tol_sup_value = (self.dimension.nominal + self.dimension.tol_sup).magnitude if self.dimension.tol_sup is not None else None
        if tol_sup_value is not None:
            self.hyst_axes.axvline(tol_sup_value, color='teal', linestyle=':', linewidth=2, label=f'Tol. Sup: {tol_sup_value:.4f}')
        
        # Vertical line for the lower tolerance
        tol_inf_value = (self.dimension.nominal + self.dimension.tol_inf).magnitude if self.dimension.tol_inf is not None else None
        if tol_inf_value is not None:
            self.hyst_axes.axvline(tol_inf_value, color='orange', linestyle=':', linewidth=2, label=f'Tol. Inf: {tol_inf_value:.4f}')
        
        self.hyst_axes.set_xlabel(self.xlabel)
        self.hyst_axes.set_ylabel(self.ylabel)
        self.hyst_axes.set_title(self.title)
        self.hyst_axes.legend()
        self.hyst_axes.grid(True, alpha=0.3)

    def show_plot(self):
        self.plot()
        if self.hyst_plot is not None:
            self.hyst_plot.show()
        else:
            print("The histogram has not been generated. Please call the plot() method before show().")

    def plot_to_base64_png(self):
        self.plot()
        buffer = io.BytesIO()
        self.hyst_plot.savefig(buffer, format='png')
        plt.close(self.hyst_plot)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('ascii')