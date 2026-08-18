from app.skills.builtin.cuda_build_diagnosis import (
    _classify_findings,
    _recommended_checks,
    _search_keywords,
)


def test_classifies_missing_nvcc():
    category, codes = _classify_findings(
        "error: command 'nvcc' failed: No such file or directory"
    )

    assert category == "cuda_toolchain"
    assert "NVCC_NOT_FOUND" in codes
    assert "CUDA_HOME" in _search_keywords(codes)
    assert _recommended_checks(codes)


def test_classifies_extension_abi_mismatch():
    category, codes = _classify_findings(
        "ImportError: extension.so: undefined symbol: _ZN2at..."
    )

    assert category == "extension_abi"
    assert codes == ["EXTENSION_ABI_MISMATCH"]


def test_unknown_build_failure_stays_conservative():
    category, codes = _classify_findings("generic compiler failure")

    assert category == "unknown_cuda_build"
    assert codes == ["CUDA_BUILD_FAILURE_UNCLASSIFIED"]
