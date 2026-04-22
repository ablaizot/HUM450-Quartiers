"""
Search for place names in an Excel file.
"""
import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

# Try to import Levenshtein for faster fuzzy matching
try:
    from Levenshtein import distance as levenshtein_distance
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False


def load_place_names_from_path(path_str: str) -> List[str]:
    """
    Load place names from either a single file or from all files in a directory.
    Removes duplicate place names automatically.
    
    Args:
        path_str: Path to a file or directory
    
    Returns:
        List of unique place names read from the file(s)
    
    Raises:
        FileNotFoundError: If the path doesn't exist
        ValueError: If a directory is empty
    """
    path = Path(path_str)
    place_names_set = set()
    
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    
    if path.is_dir():
        # Read all files in the directory
        files = [f for f in path.iterdir() if f.is_file()]
        if not files:
            raise ValueError(f"No files found in directory: {path}")
        
        print(f"📁 Reading from {len(files)} file(s) in directory: {path}")
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_names = [line.strip() for line in f if line.strip()]
                    initial_count = len(place_names_set)
                    place_names_set.update(file_names)
                    new_count = len(place_names_set) - initial_count
                    print(f"  ✓ {file_path.name}: {len(file_names)} place name(s) read, {new_count} new unique")
            except Exception as e:
                print(f"  ⚠ Warning: Could not read {file_path.name}: {e}")
    else:
        # Read single file
        with open(path, 'r', encoding='utf-8') as f:
            file_names = [line.strip() for line in f if line.strip()]
            place_names_set.update(file_names)
        print(f"📄 Reading from file: {path.name} ({len(file_names)} place name(s) read, {len(place_names_set)} unique)")
    
    place_names = sorted(list(place_names_set))
    print(f"📋 Total unique place names loaded: {len(place_names)}")
    return place_names


def find_location_column(df: pd.DataFrame, sheet_name: str) -> str:
    """
    Find a location column in the dataframe.
    First tries to find columns named LOC or similar.
    If not found, prompts the user to select one.
    
    Args:
        df: pandas DataFrame
        sheet_name: name of the sheet
    
    Returns:
        The column name to search in
    """
    # List of possible location column names
    location_keywords = ['loc', 'location', 'lieu', 'adresse', 'address', 'place', 'endroit', 'quartier', 'district']
    
    # Try to find a matching column (case-insensitive)
    for col in df.columns:
        if col.lower() in location_keywords:
            print(f"✓ Found location column '{col}' in sheet '{sheet_name}'")
            return col
    
    # If not found, prompt user
    print(f"\n⚠ No obvious location column found in sheet '{sheet_name}'")
    print("Available columns:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    while True:
        try:
            choice = input("\nSelect the column number to search in: ").strip()
            choice_int = int(choice)
            if 1 <= choice_int <= len(df.columns):
                selected_col = df.columns[choice_int - 1]
                print(f"✓ Selected column: {selected_col}\n")
                return selected_col
            else:
                print(f"Please enter a number between 1 and {len(df.columns)}")
        except ValueError:
            print("Please enter a valid number")

def isMatch(cell_value: str, place_name: str, case_sensitive: bool, threshold: float = 0.85) -> bool:
    """
    Check if a place name matches in a cell value using exact or fuzzy matching.
    
    Args:
        cell_value: The cell content to search in
        place_name: The place name to search for
        case_sensitive: Whether to be case-sensitive
        threshold: Similarity threshold (0-1) for fuzzy matching. 
                  1.0 = exact match only, 0.85 = allows ~15% character differences
    
    Returns:
        True if an exact or fuzzy match is found
    """
    # Normalize for case-insensitive search
    if not case_sensitive:
        search_text = cell_value.lower()
        search_term = place_name.lower()
    else:
        search_text = cell_value
        search_term = place_name
    
    # 1. Check for exact substring match first (fastest)
    if search_term in search_text:
        return True
    
    # 2. Fuzzy matching using Levenshtein distance
    # Split cell value into words and check similarity with place_name
    words = search_text.split()
    
    for word in words:
        similarity = calculate_similarity(search_term, word)
        if similarity >= threshold:
            #print(similarity)
            return True
    
    # 3. Try matching place_name words against cell_value words
    # This helps when place_name has multiple words (e.g., "En Prélaz")
    """place_words = search_term.split()
    for place_word in place_words:
        for cell_word in words:
            similarity = calculate_similarity(place_word, cell_word)
            if similarity >= threshold:
                return True
    
    return False"""


def calculate_similarity(s1: str, s2: str) -> float:
    """
    Calculate similarity between two strings using Levenshtein distance.
    Uses the external Levenshtein library if available, otherwise uses difflib.
    
    Args:
        s1: First string
        s2: Second string
    
    Returns:
        Similarity score from 0 to 1 (1 = identical)
    """
    if HAS_LEVENSHTEIN:
        # Using python-Levenshtein (faster)
        max_length = min(len(s1), len(s2))
        if max_length == 0:
            return 1.0
        distance = levenshtein_distance(s1, s2)
        return 1 - (distance / max_length)
    else:
        # Fallback to difflib (slower but no external dependency)
        return SequenceMatcher(None, s1, s2).ratio()

def search_place_names(
    excel_file: str,
    place_names: List[str],
    case_sensitive: bool = False,
    fuzzy_threshold: float = 0.85
) -> Dict[str, List[Dict]]:
    """
    Search for place names in a location column of an Excel file.
    Automatically identifies the location column or prompts the user to select one.
    Uses exact and fuzzy matching with Levenshtein distance.
    
    Args:
        excel_file: Path to the Excel file
        place_names: List of place names to search for
        case_sensitive: Whether the search should be case-sensitive
        fuzzy_threshold: Similarity threshold (0-1) for fuzzy matching
    
    Returns:
        Dictionary with place name as keys and lists of match results as values.
        Each result contains: sheet, row, column, cell_value, place_name_found
    """
    excel_file = Path(excel_file)
    
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file}")
    
    if not excel_file.suffix.lower() in ['.xlsx', '.xls']:
        raise ValueError(f"File must be an Excel file (.xlsx or .xls): {excel_file}")
    
    # Initialize result buckets for each target place name
    results = {place_name: [] for place_name in place_names}
    
    try:
        # Read all sheets
        xls = pd.ExcelFile(excel_file)
        print(f"Found {len(xls.sheet_names)} sheets: {xls.sheet_names}\n")
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            # Find the location column
            location_col = find_location_column(df, sheet_name)
            
            # Search through the location column only
            for row_idx, cell_value in df[location_col].items():
                if pd.isna(cell_value):
                    continue
                
                cell_str = str(cell_value)
                
                for place_name in place_names:
                    # Use the isMatch function with fuzzy matching
                    if isMatch(cell_str, place_name, case_sensitive, fuzzy_threshold):
                        # Get the entire row
                        row_data = df.iloc[row_idx].to_dict()
                        results[place_name].append({
                            'row': row_idx + 2,  # +2 because pandas uses 0-indexing and excluding header
                            'column': location_col,
                            'cell_value': cell_str,
                            'place_name': place_name,
                            'sheet': sheet_name,
                            'row_data': row_data
                        })
    
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise
    
    return results


def sanitize_sheet_name(name: str) -> str:
    """Make sheet names valid for Excel: <=31 chars, no invalid chars."""
    invalid = ['\n', '\r', '\t', ':', '\\', '/', '?', '*', '[', ']']
    sanitized = ''.join('_' if c in invalid else c for c in name)
    sanitized = sanitized[:31]
    if len(sanitized.strip()) == 0:
        sanitized = 'Sheet'
    return sanitized


def save_results(results: Dict[str, List[Dict]], excel_file: str, output_filename: str = None) -> str:
    """
    Save search results to an Excel file with name derived from the Excel file.

    Each place name gets its own sheet.

    Args:
        results: Dictionary of search results, keyed by place name
        excel_file: Path to the original Excel file
        output_filename: Optional custom output filename. If None, uses default naming.

    Returns:
        Path to the output file
    """
    filtered_results = {name: matches for name, matches in results.items() if matches}
    if not filtered_results:
        print("No matches found. No output file created.")
        return ""

    excel_path = Path(excel_file)
    if output_filename:
        output_file = excel_path.parent.parent / "Resultats" / output_filename
    else:
        output_file = excel_path.parent.parent / "Resultats" / f"{excel_path.stem}_results.xlsx"

    total_matches = sum(len(matches) for matches in filtered_results.values())

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for place_name, matches in filtered_results.items():
            # Prepare per-place data
            row_entries = []
            for match in matches:
                row_entry = {
                    'Original Sheet': match['sheet'],
                    'Row': match['row'],
                    'Place Name Found': match['place_name'],
                    'Cell Value': match['cell_value']
                }
                for col_name, col_value in match['row_data'].items():
                    row_entry[f"Original_{col_name}"] = col_value
                row_entries.append(row_entry)

            df_output = pd.DataFrame(row_entries)
            sheet_name = sanitize_sheet_name(place_name)
            df_output.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\n✓ Results saved to: {output_file}")
    print(f"  Total matches: {total_matches}")
    return str(output_file)


def print_results(results: Dict[str, List[Dict]]) -> None:
    """Pretty print search results to console."""
    if not results:
        print("No matches found.")
        return

    total_matches = sum(len(matches) for matches in results.values())
    print(f"\nFound {total_matches} match(es):\n")
    print("=" * 100)

    for place_name, matches in results.items():
        print(f"\nPlace name: {place_name}")
        print("-" * 100)

        if not matches:
            print("  No matches")
            continue

        for match in matches:
            print(f"  Row {match['row']}, Column '{match['column']}', Sheet '{match['sheet']}'")
            print(f"    Cell value: {match['cell_value'][:100]}")  # Limit to 100 chars
            print()


def main():
    """Main function to run the search interactively."""
    if len(sys.argv) < 2:
        print("Usage: python recherche_annuaires.py <excel_file> [place_names_file_or_directory]")
        print("\nInteractive mode:")
        excel_file = input("Enter the path to the Excel file: ").strip()
    else:
        excel_file = sys.argv[1]
    
    # Get place names
    if len(sys.argv) > 2:
        nameSource = sys.argv[2]
        try:
            place_names = load_place_names_from_path(nameSource)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            return
    else:
        print("Enter place names to search for (one per line, empty line to start search):")
        place_names = []
        while True:
            place_name = input("> ").strip()
            if not place_name:
                break
            place_names.append(place_name)
    
    if not place_names:
        print("No place names provided.")
        return
    
    print(f"\nSearching for {len(place_names)} place name(s)")
    print(f"File: {excel_file}")
    print(f"Matching mode: Fuzzy (Levenshtein distance)" if HAS_LEVENSHTEIN else "Matching mode: Fuzzy (difflib)")
    print()
    
    results = search_place_names(excel_file, place_names)
    #print_results(results)
    
    # Ask user for output filename
    output_filename = input("\nEnter output filename (press Enter for default naming): ").strip()
    if not output_filename:
        output_filename = None
    elif not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    
    save_results(results, excel_file, output_filename)


if __name__ == "__main__":
    main()
