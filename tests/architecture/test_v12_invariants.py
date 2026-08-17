from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'src'/'tms'
def test_telethon_has_no_hidden_rpc_retry_or_flood_sleep():
    text=(ROOT/'telegram'/'client_manager.py').read_text(encoding='utf-8');assert 'request_retries=0' in text;assert 'flood_sleep_threshold=0' in text;assert 'raise_last_call_error=True' in text
def test_watchdog_and_indefinite_rate_limit_policy_exist():
    executor=(ROOT/'migration'/'executor.py').read_text(encoding='utf-8');mapper=(ROOT/'telegram'/'error_mapper.py').read_text(encoding='utf-8');assert 'asyncio.wait_for' in executor;assert 'RPC_WATCHDOG_SECONDS' in executor;assert 'RATE_LIMIT_INDEFINITE' in mapper
