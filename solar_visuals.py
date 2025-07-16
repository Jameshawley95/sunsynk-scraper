import math

# Simple coloured block bar per 100W
def build_coloured_bar(icon, label, value, unit, colour_code):
    blocks = max(1, value // unit)
    bar = ''.join(f"\u001b[1;{colour_code};48m█\u001b[0m" for _ in range(blocks))
    return f"\u001b[0;1m{icon} {label:<7}\u001b[1;37m{value:>4}W \u001b[0m  {bar}"

# Battery bar by % with blue blocks and remaining light grey
def build_battery_bar(soc, length=15):
    filled = math.ceil((soc / 100) * length)
    filled = min(filled, length)
    empty = length - filled
    blue = ''.join("\u001b[1;34;48m█\u001b[0m" for _ in range(filled))
    empty_part = '░' * empty
    return f"\u001b[0;1m🔋 Battery:\u001b[0m\u001b[1;37m{soc:>4}%\u001b[0m  {blue}{empty_part}"

# All sunsync values for W are positive, so we need to check if we are exporting or importing
def calculate_grid_flow(pv_value: int, load_value: int, battery_power_watts: int, actual_grid_value: int) -> int:
    expected_grid_flow = pv_value - load_value - battery_power_watts
    exporting = expected_grid_flow > 50  # 50W buffer
    return -abs(actual_grid_value) if exporting else actual_grid_value

def build_grid_bar(grid_value: int) -> str:
    grid_bar_blocks = max(1, abs(grid_value) // 100)
    grid_bar_visual = ''.join(f"\u001b[1;33;48m█\u001b[0m" for _ in range(grid_bar_blocks))
    grid_emoji = " 🤑" if grid_value < 0 else ""
    return f"\u001b[0;1m🔌 Grid: \u001b[1;37m{grid_value:>5}W \u001b[0m  {grid_bar_visual}{grid_emoji}"
