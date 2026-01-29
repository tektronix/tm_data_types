"""Test the benchmark of how well the system performs reading and writing files."""

import os
import tempfile
import timeit

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from numpy.typing import NDArray

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.datum import Datum
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.helpers.byte_data_types import Short
from tm_data_types.io_factory_methods import (
    read_file,
    read_files_in_parallel,
    write_file,
    write_files_in_parallel,
)


@dataclass
class Performance:
    """A class to hold the performance data of the system."""

    total_write_times: NDArray
    writes_per_second: NDArray
    total_read_times: NDArray
    reads_per_second: NDArray


def write_files_serial(file_paths: List[str], datums: List[AnalogWaveform]) -> None:
    """Write to the provided file paths using the waveforms serially.

    Args:
        file_paths: The file paths to read from.
        datums: The waveforms that are being written.
    """
    for file_path, datum in zip(file_paths, datums, strict=False):
        write_file(file_path, datum)


def read_files_serial(file_paths: List[str]) -> None:
    """Read the provided file paths serially.

    Args:
        file_paths: The file paths to read from.
    """
    for file_path in file_paths:
        read_file(file_path)


class BenchMark:
    """A class to benchmark the performance of the system."""

    def __init__(self, name: str, show_graphs: bool = False) -> None:
        """Create a benchmark object to measure the performance of the system."""
        self.results: Optional[Performance] = None
        self.graphs: bool = show_graphs
        self.name = name

    # pylint: disable=too-many-arguments
    @staticmethod
    def plot_graph(
        name: str,
        curve_lengths: NDArray[np.float64],
        file_counts: NDArray[np.float64],
        time_values: NDArray[np.float64],
        z_axis_label: str,
        scatter_colors: str | NDArray[np.int64],
        view_tuple: Tuple[int, int],
    ) -> None:
        """Plot a mesh of values on a scatter plot graph.

        Args:
            name: The title of the graph
            curve_lengths: An array of curve lengths for the x axis.
            file_counts: An array of file counts for the y axis.
            time_values: A matrix of time counts for the z axis.
            z_axis_label: The label for the z axis.
            scatter_colors: The colors for the scatter plot.
            view_tuple: What view the scatter plot should take.
        """
        # create a grid for the scatter plot
        mesh_curve_length, mesh_file_count = np.meshgrid(
            np.arange(curve_lengths.shape[0]),
            np.arange(file_counts.shape[0]),
        )

        fig = plt.figure()
        ax = plt.axes(projection="3d")
        # create scatter plot
        ax.plot_wireframe(mesh_curve_length, mesh_file_count, time_values.T, color="black")
        ax.scatter(mesh_curve_length, mesh_file_count, time_values.T, color=scatter_colors)
        ax.set_title(name)
        # setup x axis
        ax.set_xlabel("Curve Length (S)", fontsize=12)
        ax.xaxis.set_ticks(np.arange(curve_lengths.shape[0]))
        ax.xaxis.set_ticklabels(curve_lengths.astype(np.uint32))
        # setup y axis
        ax.set_ylabel("File Count (#)", fontsize=12)
        ax.yaxis.set_ticks(np.arange(file_counts.shape[0]))
        ax.yaxis.set_ticklabels(file_counts.astype(np.uint32))
        # setup z axis
        ax.set_zlabel(z_axis_label, fontsize=12)
        ax.view_init(view_tuple[0], view_tuple[1])
        # plot
        fig.show()

    def create_timing_graphs(
        self,
        name: str,
        curve_lengths: NDArray[np.float64],
        file_counts: NDArray[np.float64],
        total_times: NDArray[np.float64],
        amount_per_second: NDArray[np.float64],
    ) -> None:
        """Create two graphs for representing some performance thresholds of the data.

        Args:
            name: The name of the action and the name of the process.
            curve_lengths: An array of curve lengths for the x axis.
            file_counts: An array of file counts for the y axis.
            total_times: A matrix of total time taken for the z axis.
            amount_per_second: A matrix of time taken per file for the z axis.
        """
        self.plot_graph(
            name=f"{name} Time vs Datum Count and Datum Length",
            curve_lengths=curve_lengths,
            file_counts=file_counts,
            time_values=total_times,
            z_axis_label="Time (s)",
            scatter_colors="blue",
            view_tuple=(30, -145),
        )
        col = np.where(
            amount_per_second < 500,
            "red",
            np.where(amount_per_second < 1000, "yellow", "green"),
        ).T.flatten()
        self.plot_graph(
            name=f"{name} Files per second vs Datum Count and Datum Length",
            curve_lengths=curve_lengths,
            file_counts=file_counts,
            time_values=amount_per_second,
            z_axis_label="Files Per Second (#/s)",
            scatter_colors=col,
            view_tuple=(30, -45),
        )

    # pylint: disable=too-many-locals
    def measure_times(
        self,
        write_method: Callable[[List[str], List[Datum]], None],
        read_method: Callable[[List[str]], None],
        curve_lengths: List[int],
        file_counts: List[int],
    ) -> None:
        """Measure the time for the provided range of curve lengths and file counts.

        Args:
            write_method: What method will be used to write.
            read_method: What method will be used to read.
            curve_lengths: The range of powers that will be used to determine curve lengths.
            file_counts: The range of powers that will be used to determine file counts.
        """
        x_length = len(curve_lengths)
        y_length = len(file_counts)
        total_write_times = np.empty((x_length, y_length))
        writes_per_second = np.empty((x_length, y_length))
        total_read_times = np.empty((x_length, y_length))
        reads_per_second = np.empty((x_length, y_length))

        with tempfile.TemporaryDirectory() as waveform_directory:
            for length_index, buffer_length in enumerate(curve_lengths):
                x_points = np.linspace(0, 1, buffer_length)
                sin_data: NDArray[np.float64] = np.sin(2 * np.pi * x_points)

                sin_wave = AnalogWaveform()
                sin_wave.y_axis_values = sin_data
                sin_wave.y_axis_extent_magnitude = 0.1
                sin_wave.y_axis_offset = 0.0
                sin_wave.x_axis_spacing = 1.0e-7

                sin_wave.measured_data = RawSample(sin_wave.y_axis_values, as_type=Short)

                for count_index, count in enumerate(file_counts):
                    file_names = [
                        f"{waveform_directory}/index_{index}.wfm" for index in range(count)
                    ]

                    datums = [sin_wave] * count

                    start_time = timeit.default_timer()
                    write_method(file_names, datums)

                    end_time = timeit.default_timer()
                    time_summation = end_time - start_time
                    print(
                        f"Finished {self.name} write File Count: {count} "
                        f"Curve Length: {buffer_length} "
                        f"time: {time_summation} file_per_second: {count / time_summation}",
                    )
                    total_write_times[length_index][count_index] = time_summation
                    writes_per_second[length_index][count_index] = count / time_summation
                    start_time = timeit.default_timer()
                    read_method(file_names)
                    end_time = timeit.default_timer()
                    time_summation = end_time - start_time
                    print(
                        f"Finished {self.name} read File Count: {count} "
                        f"Curve Length: {buffer_length} "
                        f"time: {time_summation} file_per_second: {count / time_summation}",
                    )
                    print(
                        f"Verify number of files in directory: "
                        f"{len(os.listdir(waveform_directory))}"
                    )
                    print(
                        f"Verify datum length with one waveform: "
                        f"{np.shape(sin_wave.y_axis_values)[0]}",
                    )
                    total_read_times[length_index][count_index] = time_summation
                    reads_per_second[length_index][count_index] = count / time_summation

        self.results = Performance(
            total_write_times=total_write_times,
            total_read_times=total_read_times,
            writes_per_second=writes_per_second,
            reads_per_second=reads_per_second,
        )
        if self.graphs:
            self.create_timing_graphs(
                f"{self.name} Write",
                curve_lengths,
                file_counts,
                total_write_times,
                writes_per_second,
            )
            self.create_timing_graphs(
                f"{self.name} Read",
                curve_lengths,
                file_counts,
                total_read_times,
                reads_per_second,
            )


def run_benchmark() -> None:
    """Run the benchmark tests for both parallel and serial file read/write methods."""
    benchmark_parallel = BenchMark("Parallel")
    benchmark_parallel.measure_times(
        write_method=write_files_in_parallel,
        read_method=read_files_in_parallel,
        curve_lengths=[1000, 5000, 10000, 50000],
        file_counts=[1000, 5000, 10000, 50000],
    )
    benchmark_serial = BenchMark("Serial")
    benchmark_serial.measure_times(
        write_method=write_files_serial,
        read_method=read_files_serial,
        curve_lengths=[1000, 5000, 10000, 50000],
        file_counts=[1000, 5000, 10000, 50000],
    )

    for benchmark in benchmark_serial, benchmark_parallel:
        for key, item in asdict(benchmark.results).items():
            np.savetxt(
                f"temp_{benchmark.name}_{key}.txt",
                item,
                delimiter=",",
                fmt="%10.3e",
                comments="",
            )


if __name__ == "__main__":
    run_benchmark()
