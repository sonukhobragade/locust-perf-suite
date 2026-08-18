"""
Data Loader Utility
Handles loading test data from CSV files
"""
import csv
import logging
from typing import List, Dict


def load_user_ids_from_csv(file_path: str, user_id_column: int = 0) -> List[str]:
    """
    Load user IDs from a CSV file

    Args:
        file_path: Path to the CSV file
        user_id_column: Column index containing user IDs (default: 0)

    Returns:
        List of user IDs as strings
    """
    user_ids = []
    try:
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader, None)  # Skip header if exists
            for row in csv_reader:
                try:
                    if len(row) > user_id_column:
                        user_ids.append(str(row[user_id_column]))
                except (IndexError, ValueError) as e:
                    logging.warning(f"Skipping invalid row: {e}")
                    continue
        logging.info(f"Loaded {len(user_ids)} user IDs from {file_path}")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error loading user IDs: {e}")

    return user_ids


def load_test_data_from_csv(file_path: str) -> List[Dict]:
    """
    Load test data from a CSV file as list of dictionaries

    Args:
        file_path: Path to the CSV file

    Returns:
        List of dictionaries with column names as keys
    """
    test_data = []
    try:
        with open(file_path, 'r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                test_data.append(dict(row))
        logging.info(f"Loaded {len(test_data)} test data rows from {file_path}")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error loading test data: {e}")

    return test_data
