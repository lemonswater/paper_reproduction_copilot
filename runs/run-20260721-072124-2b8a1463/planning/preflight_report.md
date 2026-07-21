# Preflight Report

## Summary

- Action ID: `action_d97462c795f9`
- Action Hash: `e944fea56b9bc1fa84c5d0d4806822e214d1bd362502a8483ce8f6c0807d13c7`
- Ready To Execute: `True`
- Generated At: `2026-07-21T07:54:39.339034+00:00`
- Summary: preflight passed: no blocking issues detected

## Items

### working_directory_exists

- Category: `static`
- Status: `passed`
- Evidence: working directory exists: /data/tianshaoqi24/P4Transformer

### working_directory_writable

- Category: `static`
- Status: `passed`
- Evidence: working directory is writable: /data/tianshaoqi24/P4Transformer

### program_in_path

- Category: `static`
- Status: `passed`
- Evidence: program resolved to: /home/tianshaoqi24/miniconda3/envs/3d/bin/python

### command_placeholders_resolved

- Category: `static`
- Status: `passed`
- Evidence: no unresolved placeholders detected in command arguments

### entry_script_exists

- Category: `static`
- Status: `passed`
- Evidence: entry script exists: /data/tianshaoqi24/P4Transformer/train-msr-small.py

### dependency_manifest_detected

- Category: `static`
- Status: `warning`
- Evidence: no requirements.txt / pyproject.toml / environment.yml detected
- Recommendation: 后续可以从 README 或安装脚本中补充依赖来源。

### python_version_probe

- Category: `runtime`
- Status: `passed`
- Evidence: Python 3.8.16


### torch_import_probe

- Category: `runtime`
- Status: `passed`
- Evidence: 1.10.1+cu113


### cuda_available_probe

- Category: `runtime`
- Status: `passed`
- Evidence: True

