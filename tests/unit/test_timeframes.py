import numpy as np
from openscm import timeframes
import pytest

possible_source_values = [[1, 5, 3, 5, 7, 3, 2, 9]]

possible_target_values = {
    (0, 10, 4, 7, 0): [
        2.02142857,
        5.37857143,
        3.42857143,
        3.34285714,
        5.1,
        7.18571429,
        5.44642857,
        2.49642857,
        1.20714286,
        5.59285714,
        10.4,
    ],
    (0, 10, 0, 5, 0): [
        0.0,
        2.0,
        4.75,
        5.25,
        3.0,
        3.0,
        4.5,
        5.5,
        7.25,
        6.75,
        3.625,
        2.375,
        1.25,
        2.75,
        7.25,
        10.75,
    ],
    (3, 3, 0, 5, 0): [-0.77777778, 4.13333333, 4.13333333, 5.51666667, 5.05952381],
}


@pytest.fixture(params=[(0, 10), (3, 3)])
def source(request):
    return timeframes.Timeframe(
        start_time=request.param[0], period_length=request.param[1]
    )


@pytest.fixture(params=[(4, 7), (0, 5)])
def target(request):
    return timeframes.Timeframe(
        start_time=request.param[0], period_length=request.param[1]
    )


@pytest.fixture(params=range(len(possible_source_values)))
def source_values_index(request):
    return request.param


def get_source_values(source_values_index):
    return np.array(possible_source_values[source_values_index])


def get_test_values(source, target, source_values_index):
    result = possible_target_values.get(
        (
            source.start_time,
            source.period_length,
            target.start_time,
            target.period_length,
            source_values_index,
        ),
        None,
    )
    if result is None:
        return None, None
    else:
        return get_source_values(source_values_index), np.array(result)


def test_conversion_to_same_timeframe(source, source_values_index):
    source_values = get_source_values(source_values_index)
    target_values = timeframes._convert(source_values, source, source)
    np.testing.assert_array_equal(target_values, source_values)


def test_insufficient_overlap(source, target):
    with pytest.raises(timeframes.InsufficientDataError):
        timeframes.TimeframeConverter(
            source, timeframes.Timeframe(-1000, target.period_length)
        )


def test_short_data(source, target):
    for a in [[], [0], [0, 1]]:
        with pytest.raises(timeframes.InsufficientDataError):
            timeframes._convert_cached(np.array(a), source, target, None)


def test_conversion(source, target, source_values_index):
    source_values, target_values = get_test_values(source, target, source_values_index)
    if target_values is not None:
        values = timeframes._convert(source_values, source, target)
        np.testing.assert_allclose(values, target_values)
        assert len(values) == target.get_length_until(
            source.get_stop_time(len(source_values))
        )


def test_timeframeconverter(source, target, source_values_index):
    source_values, target_values = get_test_values(source, target, source_values_index)
    if target_values is not None:
        timeframeconverter = timeframes.TimeframeConverter(source, target)
        assert timeframeconverter.get_target_len(len(source_values)) == len(
            target_values
        )
        values = timeframeconverter.convert_from(source_values)
        np.testing.assert_allclose(values, target_values)

        timeframeconverter = timeframes.TimeframeConverter(target, source)
        assert timeframeconverter.get_source_len(len(source_values)) == len(
            target_values
        )
        values = timeframeconverter.convert_to(source_values)
        np.testing.assert_allclose(values, target_values)


def test_cache(source, target):
    timeframeconverter = timeframes.TimeframeConverter(source, target)
    for source_values_index in range(len(possible_source_values)):
        source_values, target_values = get_test_values(
            timeframeconverter.source, timeframeconverter.target, source_values_index
        )
        if target_values is not None:
            values = timeframeconverter.convert_from(source_values)
            np.testing.assert_allclose(values, target_values)
            values = timeframeconverter.convert_from(source_values)
            np.testing.assert_allclose(values, target_values)


def test_timeframe_repr(source):
    assert repr(
        source
    ) == "<openscm.timeframes.Timeframe(start_time={}, period_length={})>".format(
        source.start_time, source.period_length
    )