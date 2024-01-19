import pandas as pd

def pandas_settings() -> None:
    for option in ('display.max_rows', 'display.max_columns', 'display.width', 'display.memory_usage'):
        pd.set_option(option, 250 if 'memory_usage' not in option else False)
    # message('pandas')
    return None

# if __name__ == "__main__":
if __name__ == "customsettings":
    pandas_settings()