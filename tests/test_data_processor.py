import pytest
import pandas as pd
from app.data_processor import DataProcessor
from app.config import DataDirectories


@pytest.fixture
def data_processor():
    return DataProcessor(
        DataDirectories.CURRENT_DATA_DIR,
        DataDirectories.PREVIOUS_DATA_DIR,
        DataDirectories.CHANGES_DATA_DIR,
    )


@pytest.fixture
def current_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "salePriceU_current": [100, 150, 200, 0],
        }
    )


@pytest.fixture
def previous_df():
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "salePriceU_previous": [110, 160, 220, 300],
        }
    )


@pytest.fixture
def mock_calculate_percent_change(monkeypatch):
    def mock_percent_change(current, previous):
        return ((current - previous) / previous) * 100

    monkeypatch.setattr(DataProcessor, "calculate_percent_change", mock_percent_change)


@pytest.mark.asyncio
async def test_process_file_basic_functionality(
    data_processor,
    current_df,
    previous_df,
):
    columns_to_include = [
        "id",
        "salePriceU_current",
        "salePriceU_previous",
        "percent_change",
    ]
    price_difference_percentage = 7

    # Await the async function
    result_df = await data_processor.process_file(
        current_df=current_df,
        previous_df=previous_df,
        columns_to_include=columns_to_include,
        price_difference_percentage=price_difference_percentage,
    )
    print(result_df)  # Debug: Check the actual output of result_df
    expected_df = pd.DataFrame(
        {
            "id": [1, 3],
            "salePriceU_current": [100, 200],
            "salePriceU_previous": [110, 220],
            "percent_change": [-9.090909090909092, -9.090909090909092],
        }
    )

    pd.testing.assert_frame_equal(result_df.reset_index(drop=True), expected_df)


@pytest.mark.asyncio
async def test_no_rows_meet_price_difference_threshold(
    data_processor,
    current_df,
    previous_df,
):
    columns_to_include = [
        "id",
        "salePriceU_current",
        "salePriceU_previous",
        "percent_change",
    ]
    price_difference_percentage = 50

    result_df = await data_processor.process_file(
        current_df=current_df,
        previous_df=previous_df,
        columns_to_include=columns_to_include,
        price_difference_percentage=price_difference_percentage,
    )

    assert result_df.empty


@pytest.mark.asyncio
async def test_included_columns_only(
    data_processor,
    current_df,
    previous_df,
):
    columns_to_include = ["id", "salePriceU_current"]
    price_difference_percentage = 5

    result_df = await data_processor.process_file(
        current_df=current_df,
        previous_df=previous_df,
        columns_to_include=columns_to_include,
        price_difference_percentage=price_difference_percentage,
    )

    assert list(result_df.columns) == columns_to_include
