"""Test cloud_storage.py: config loading, credential checks, and OBS upload/
download/sync logic against a mocked ObsClient (no real Huawei Cloud calls).

Run: python -m tests.test_cloud_storage
"""
from __future__ import annotations

import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

ATTEMPT_ROOT = Path(__file__).resolve().parents[1]
SHARED_SRC = ATTEMPT_ROOT / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

import cloud_storage  # noqa: E402


def run_test(func, *args, **kwargs):
    start = time.perf_counter()
    try:
        res = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        print(f" [SUCCESS] 函数: {func.__name__} | 耗时: {duration:.2f}ms")
        print(f" 输入: {args} {kwargs}")
        print(f" 输出: {res}")
        return res
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        print(f" [FAILED] 函数: {func.__name__} | 耗时: {duration:.2f}ms | 错误原因: {e}")
        raise


@dataclass
class _PipelineCfgStub:
    data_root: Path
    dataset_name: str = "technology_cultivation_00"


class _FakeResponse(SimpleNamespace):
    """Mimics obs.model.GetResult: has .status, .errorMessage, .body."""


class _FakeObsClient:
    """Records every call so tests can assert on bucket/key/path arguments."""

    calls: list[tuple[str, tuple, dict]] = []

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        _FakeObsClient.calls.append(("__init__", (), kwargs))

    def putFile(self, bucket, key, file_path, **kwargs):
        _FakeObsClient.calls.append(("putFile", (bucket, key, file_path), kwargs))
        return _FakeResponse(status=200, errorMessage=None)

    def getObject(self, bucket, key, downloadPath=None, **kwargs):
        _FakeObsClient.calls.append(("getObject", (bucket, key, downloadPath), kwargs))
        Path(downloadPath).write_text("fake content from OBS", encoding="utf-8")
        return _FakeResponse(status=200, errorMessage=None)

    def listObjects(self, bucket, prefix=None, **kwargs):
        _FakeObsClient.calls.append(("listObjects", (bucket, prefix), kwargs))
        content = SimpleNamespace(key=f"{prefix}fake.jsonl")
        return _FakeResponse(status=200, errorMessage=None, body=SimpleNamespace(contents=[content]))

    def close(self):
        pass


class _FailingObsClient(_FakeObsClient):
    def putFile(self, bucket, key, file_path, **kwargs):
        return _FakeResponse(status=403, errorMessage="AccessDenied")


def _install_fake_obs_module(client_cls):
    fake_module = ModuleType("obs")
    fake_module.ObsClient = client_cls
    return mock.patch.dict(sys.modules, {"obs": fake_module})


def test_load_cloud_storage_config_missing_file():
    """Missing config file should return a safe disabled default, not raise."""
    print("\n=== test_load_cloud_storage_config_missing_file ===")
    with tempfile.TemporaryDirectory() as tmp:
        missing_path = Path(tmp) / "does_not_exist.yaml"
        cfg = run_test(cloud_storage.load_cloud_storage_config, missing_path)
        assert cfg == {"enabled": False, "sync_targets": []}


def test_load_cloud_storage_config_real_file():
    """The real configs/cloud_storage.yaml should parse and default to disabled."""
    print("\n=== test_load_cloud_storage_config_real_file ===")
    cfg = run_test(cloud_storage.load_cloud_storage_config)
    assert cfg["enabled"] is False, "Expected cloud sync disabled by default"
    assert cfg["bucket"] == "predictive-agents-data"
    assert cfg["access_key_env"] == "HUAWEICLOUD_AK"
    assert cfg["secret_key_env"] == "HUAWEICLOUD_SK"


def test_get_client_missing_credentials_raises():
    """Without AK/SK in the environment, _get_client must raise, not silently fail."""
    print("\n=== test_get_client_missing_credentials_raises ===")
    cfg = {
        "endpoint": "obs.cn-north-4.myhuaweicloud.com",
        "bucket": "predictive-agents-data",
        "access_key_env": "HUAWEICLOUD_AK_TEST_UNSET",
        "secret_key_env": "HUAWEICLOUD_SK_TEST_UNSET",
    }
    with _install_fake_obs_module(_FakeObsClient):
        with mock.patch.object(cloud_storage, "_load_env", lambda: None):
            try:
                run_test(cloud_storage._get_client, cfg)
                raised = False
            except RuntimeError as e:
                print(f" [SUCCESS] 函数: _get_client | 预期抛出 RuntimeError: {e}")
                raised = True
            assert raised, "Expected RuntimeError when credentials are missing"


def test_upload_file_success():
    """upload_file should call putFile with (bucket, remote_key, local_path)."""
    print("\n=== test_upload_file_success ===")
    _FakeObsClient.calls = []
    cfg = {
        "endpoint": "obs.cn-north-4.myhuaweicloud.com",
        "bucket": "predictive-agents-data",
        "access_key_env": "HUAWEICLOUD_AK",
        "secret_key_env": "HUAWEICLOUD_SK",
    }
    with tempfile.TemporaryDirectory() as tmp:
        local_file = Path(tmp) / "sample.jsonl"
        local_file.write_text('{"a": 1}\n', encoding="utf-8")
        with _install_fake_obs_module(_FakeObsClient), \
                mock.patch.dict("os.environ", {"HUAWEICLOUD_AK": "ak", "HUAWEICLOUD_SK": "sk"}), \
                mock.patch.object(cloud_storage, "_load_env", lambda: None):
            run_test(cloud_storage.upload_file, local_file, "Processed/sample.jsonl", cfg)
        put_calls = [c for c in _FakeObsClient.calls if c[0] == "putFile"]
        assert len(put_calls) == 1
        _, args, _ = put_calls[0]
        assert args == ("predictive-agents-data", "Processed/sample.jsonl", str(local_file))


def test_upload_file_failure_raises():
    """A non-2xx OBS status must surface as RuntimeError, not be swallowed."""
    print("\n=== test_upload_file_failure_raises ===")
    cfg = {
        "endpoint": "obs.cn-north-4.myhuaweicloud.com",
        "bucket": "predictive-agents-data",
        "access_key_env": "HUAWEICLOUD_AK",
        "secret_key_env": "HUAWEICLOUD_SK",
    }
    with tempfile.TemporaryDirectory() as tmp:
        local_file = Path(tmp) / "sample.jsonl"
        local_file.write_text('{"a": 1}\n', encoding="utf-8")
        with _install_fake_obs_module(_FailingObsClient), \
                mock.patch.dict("os.environ", {"HUAWEICLOUD_AK": "ak", "HUAWEICLOUD_SK": "sk"}), \
                mock.patch.object(cloud_storage, "_load_env", lambda: None):
            try:
                run_test(cloud_storage.upload_file, local_file, "Processed/sample.jsonl", cfg)
                raised = False
            except RuntimeError as e:
                print(f" [SUCCESS] 函数: upload_file | 预期抛出 RuntimeError: {e}")
                raised = True
            assert raised, "Expected RuntimeError on non-2xx OBS status"


def test_download_file_round_trip():
    """download_file should write the OBS response body to local_path."""
    print("\n=== test_download_file_round_trip ===")
    cfg = {
        "endpoint": "obs.cn-north-4.myhuaweicloud.com",
        "bucket": "predictive-agents-data",
        "access_key_env": "HUAWEICLOUD_AK",
        "secret_key_env": "HUAWEICLOUD_SK",
    }
    with tempfile.TemporaryDirectory() as tmp:
        local_file = Path(tmp) / "nested" / "downloaded.jsonl"
        with _install_fake_obs_module(_FakeObsClient), \
                mock.patch.dict("os.environ", {"HUAWEICLOUD_AK": "ak", "HUAWEICLOUD_SK": "sk"}), \
                mock.patch.object(cloud_storage, "_load_env", lambda: None):
            run_test(cloud_storage.download_file, "Processed/sample.jsonl", local_file, cfg)
        assert local_file.exists(), "download_file must create parent dirs and write the file"
        assert local_file.read_text(encoding="utf-8") == "fake content from OBS"


def test_sync_processed_data_disabled_is_noop():
    """sync_processed_data must not touch OBS at all when huawei_obs.enabled=False."""
    print("\n=== test_sync_processed_data_disabled_is_noop ===")
    with tempfile.TemporaryDirectory() as tmp:
        pipeline_cfg = _PipelineCfgStub(data_root=Path(tmp))
        cfg = {"enabled": False, "sync_targets": []}
        uploaded = run_test(cloud_storage.sync_processed_data, pipeline_cfg, cfg)
        assert uploaded == []


def test_sync_processed_data_uploads_all_files():
    """sync_processed_data should walk Data/Processed/<dataset> and upload every file."""
    print("\n=== test_sync_processed_data_uploads_all_files ===")
    _FakeObsClient.calls = []
    with tempfile.TemporaryDirectory() as tmp:
        data_root = Path(tmp)
        dataset = "technology_cultivation_00"
        processed_dir = data_root / "Processed" / dataset
        processed_dir.mkdir(parents=True)
        (processed_dir / "pivot_table.jsonl").write_text('{"x": 1}\n', encoding="utf-8")
        (processed_dir / "pivot_table_extended.jsonl").write_text('{"x": 2}\n', encoding="utf-8")

        pipeline_cfg = _PipelineCfgStub(data_root=data_root, dataset_name=dataset)
        cfg = {
            "enabled": True,
            "endpoint": "obs.cn-north-4.myhuaweicloud.com",
            "bucket": "predictive-agents-data",
            "access_key_env": "HUAWEICLOUD_AK",
            "secret_key_env": "HUAWEICLOUD_SK",
            "sync_targets": [{"local": "Processed", "remote_prefix": "Processed", "enabled": True}],
        }
        with _install_fake_obs_module(_FakeObsClient), \
                mock.patch.dict("os.environ", {"HUAWEICLOUD_AK": "ak", "HUAWEICLOUD_SK": "sk"}), \
                mock.patch.object(cloud_storage, "_load_env", lambda: None):
            uploaded = run_test(cloud_storage.sync_processed_data, pipeline_cfg, cfg)

        assert sorted(uploaded) == [
            f"Processed/{dataset}/pivot_table.jsonl",
            f"Processed/{dataset}/pivot_table_extended.jsonl",
        ]
        put_calls = [c for c in _FakeObsClient.calls if c[0] == "putFile"]
        assert len(put_calls) == 2


def main():
    test_load_cloud_storage_config_missing_file()
    test_load_cloud_storage_config_real_file()
    test_get_client_missing_credentials_raises()
    test_upload_file_success()
    test_upload_file_failure_raises()
    test_download_file_round_trip()
    test_sync_processed_data_disabled_is_noop()
    test_sync_processed_data_uploads_all_files()
    print("\n=== All cloud_storage tests passed ===")


if __name__ == "__main__":
    main()
