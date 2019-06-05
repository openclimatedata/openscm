import numpy as np
import pandas as pd
from base import _AdapterTester

from openscm.adapters.dice import DICE
from openscm.core.parameters import ParameterType
from openscm.core.parameterset import ParameterSet
from openscm.core.time import create_time_points


def _run_and_compare(test_adapter, filename):
    original_data = pd.read_csv(filename)
    start_time = np.datetime64("2010-01-01")
    timestep_count = len(original_data)
    stop_time = start_time + (timestep_count - 1) * np.timedelta64(365, "D")

    test_adapter._parameters.generic(("Start Time")).value = start_time
    test_adapter._parameters.generic(("Stop Time")).value = stop_time
    test_adapter._parameters.generic(
        ("DICE", "forcoth_saturation_time")
    ).value = start_time + np.timedelta64(90 * 365, "D")
    time_points = create_time_points(
        start_time,
        np.timedelta64(365, "D"),
        timestep_count,
        ParameterType.AVERAGE_TIMESERIES,
    )
    test_adapter._parameters.timeseries(
        ("Emissions", "CO2"), "GtCO2/a", time_points, timeseries_type="average"
    ).values = original_data.E.values[:timestep_count]

    test_adapter.initialize_model_input()
    test_adapter.initialize_run_parameters()
    test_adapter.reset()
    test_adapter.run()

    output_parameters = [
        (("Pool", "CO2", "Atmosphere"), "GtC", "MAT"),
        (("Pool", "CO2", "Ocean", "lower"), "GtC", "ML"),
        (("Pool", "CO2", "Ocean", "shallow"), "GtC", "MU"),
        (("Radiative Forcing", "CO2"), "W/m^2", "FORC"),
        (("Surface Temperature", "Increase"), "delta_degC", "TATM"),
        (("Ocean Temperature", "Increase"), "delta_degC", "TOCEAN"),
    ]
    for name, unit, original_name in output_parameters:
        np.testing.assert_allclose(
            test_adapter._output.timeseries(
                name,
                unit,
                time_points[:-1],  # these are point timeseries
                timeseries_type="point",
            ).values,
            original_data[original_name][:timestep_count],
            err_msg="Not matching original results for variable '{}'".format(
                "|".join(name)
            ),
            rtol=1e-4,
        )


class TestMyAdapter(_AdapterTester):
    tadapter = DICE

    def test_match_original(self, test_adapter):
        _run_and_compare(test_adapter, "tests/data/dice/original_results.csv")

    def test_match_original_bau(self, test_adapter):
        _run_and_compare(test_adapter, "tests/data/dice/original_results_bau.csv")

    def prepare_run_input(self, test_adapter, start_time, stop_time):
        """
        Overload this in your adapter test if you need to set required input parameters.
        This method is called directly before ``test_adapter.initialize_model_input``
        during tests.
        """
        test_adapter._parameters.generic("Start Time").value = start_time
        test_adapter._parameters.generic("Stop Time").value = stop_time

        npoints = 10  # setting to zero so doesn't matter
        time_points_for_averages = create_time_points(
            start_time,
            stop_time - start_time,
            npoints,
            ParameterType.AVERAGE_TIMESERIES,
        )
        test_adapter._parameters.timeseries(
            ("Emissions", "CO2"),
            "GtCO2/a",
            time_points_for_averages,
            timeseries_type="average",
        ).values = np.zeros(npoints)

    def test_openscm_standard_parameters_handling(self):
        parameters = ParameterSet()

        start_t = np.datetime64("1850-01-01")
        parameters.generic("Start Time").value = start_t

        stop_t = np.datetime64("2100-01-01")
        parameters.generic("Stop Time").value = stop_t

        ecs_magnitude = 3.12
        parameters.scalar(
            "Equilibrium Climate Sensitivity", "delta_degC"
        ).value = ecs_magnitude
        parameters.scalar(
            ("DICE", "t2xco2"), "delta_degC"
        ).value = 5  # ensure openscm standard parameters take precedence

        rf2xco2_magnitude = 4.012
        parameters.scalar("Radiative Forcing 2xCO2", "W / m^2").value = rf2xco2_magnitude
        parameters.scalar(("DICE", "fco22x"), "W / m^2").value = 3.5

        output_parameters = ParameterSet()

        test_adapter = self.tadapter(parameters, output_parameters)

        self.prepare_run_input(
            test_adapter,
            parameters.generic("Start Time").value,
            parameters.generic("Stop Time").value,
        )
        test_adapter.initialize_model_input()
        test_adapter.initialize_run_parameters()
        test_adapter.reset()
        test_adapter.run()

        assert test_adapter._parameters.generic("Start Time").value == start_t
        assert test_adapter._parameters.generic("Stop Time").value == stop_t
        assert (
            test_adapter._parameters.scalar(
                "Equilibrium Climate Sensitivity", "delta_degC"
            ).value
            == ecs_magnitude
        )
        assert (
            test_adapter._parameters.scalar(("DICE", "t2xco2"), "delta_degC").value
            == ecs_magnitude
        )
        assert (
            test_adapter._parameters.scalar(
                "Radiative Forcing 2xCO2", "W/m^2"
            ).value
            == rf2xco2_magnitude
        )
        assert (
            test_adapter._parameters.scalar(("DICE", "fco22x"), "mW / m^2").value
            == rf2xco2_magnitude * 1000
        )

        assert test_adapter._values.start_time.value == start_t
        assert test_adapter._values.stop_time.value == stop_t
        assert test_adapter._values.t2xco2.value == ecs_magnitude
        assert test_adapter._values.fco22x.value == rf2xco2_magnitude

        # do we want adapters to push all parameter values to output too? If yes, uncomment this
        # assert output_parameters.generic("Start Time").value == np.datetime64("1850-01-01")
        # assert output_parameters.generic("Stop Time").value == np.datetime64("2100-01-01")
        # assert output_parameters.scalar("Equilibrium Climate Sensitivity", "delta_degC").value == ecs_magnitude
