import pandas as pd
import numpy as np

# ==========================================
# 1. SCALARS & STRINGS (Testing Sidebar Previews)
# ==========================================
meaning_of_life = 42
pi_value = 3.1415926535
short_status = "OK"
long_description = (
    "This is a very long string designed to test the truncation "
    "logic in the sidebar preview. It should be cut off..."
)
multi_line_log = """INFO: System Start
WARN: High Memory Usage
ERROR: Connection Timeout
INFO: Retrying..."""

# ==========================================
# 2. LISTS (Testing Min/Max & Type Logic)
# ==========================================
# Sidebar should show: Length: 5 | Min: 0, Max: 100
scores_list = [0, 55, 82, 99, 100] 

# Sidebar should show: Length: 3 (No min/max due to mixed types)
mixed_bag = [1, "Apple", 3.14]

# ==========================================
# 3. NUMPY ARRAYS (Testing Heatmap & Slicing)
# ==========================================
# 1D Array
vector = np.linspace(0, 10, 20)

# 2D Array - Designed for HEATMAP testing (Negatives to Positives)
# Cells should fade from Blue (Low) to Red (High)
heatmap_matrix = np.random.randint(-50, 50, (10, 8))

# 3D Array - Testing "Slice" logic
# You should see clickable "Slice 0", "Slice 1", etc.
image_data_3d = np.random.randint(0, 255, (5, 5, 3))

# 4D Array - Testing Deep Recursion
hypercube = np.zeros((2, 2, 3, 3))

# ==========================================
# 4. PANDAS DATAFRAMES (Testing Tables)
# ==========================================
# Financial Data (Good for color scaling)
df_financials = pd.DataFrame({
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    'Revenue': [10000, 12000, 15000, 11000, 16000],
    'Profit': [-500, 2000, 4500, 100, 5000], # Mix of neg/pos for colors
    'Growth_Pct': [0.0, 0.2, 0.25, -0.26, 0.45]
})

# Wide Data (Testing Horizontal Scroll & Column Resizing)
# Try dragging the column headers!
wide_data = {f"Col_{i}": np.random.rand(10) for i in range(20)}
df_wide = pd.DataFrame(wide_data)

# ==========================================
# 5. NESTED DATA (Testing Recursive Tree)
# ==========================================
# A complex dictionary containing other objects
project_config = {
    "metadata": {
        "author": "Dev",
        "created": "2023-10-27",
        "version": 1.5
    },
    "model_params": {
        "layers": [64, 128, 256],
        "dropout": 0.5,
        "active": True
    },
    # Var Viper should allow you to drill down into these:
    "datasets": {
        "train": pd.DataFrame({'x': [1,2], 'y': [3,4]}), 
        "test": np.array([1, 0, 1, 0]),
        "meta": {"source": "S3", "id": 99}
    }
}

# ==========================================
# 6. EDGE CASES
# ==========================================
empty_list = []
empty_dict = {}
single_value_array = np.array([42])
# Dictionary with tuple keys (should handle string conversion gracefully)
tuple_keys = {
    (0,0): "Origin",
    (1,0): "Right"
}

print("Test suite loaded. Ready for Var Viper inspection.")
