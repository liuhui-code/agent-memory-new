# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Portable fixed controls. Draft refuses execution until independently frozen."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / 'MANIFEST-DRAFT.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(manifest):
    for name, item in manifest['byte_identical_inputs'].items():
        assert digest(HERE / name) == item['sha256'], name
    assert digest(Path(__file__)) == manifest['runner_sha256']
    actual = {str(p.relative_to(REPO)): digest(p)
              for p in sorted((REPO / 'tools').rglob('*')) if p.is_file()}
    assert actual == manifest['runtime_sha256'], 'full runtime file set/hash changed'
    return actual


def load(name):
    spec = importlib.util.spec_from_file_location('portable_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def invoke(kind, case, folder):
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(HERE))
    if kind == 'private':
        return load('private_tamper_adapter_draft').run_private_case(case, folder)
    if kind == 'latefallback':
        return load('validation_log_latefallback_v2_draft').run_case(case, folder)
    if kind == 'budget':
        module = load('budget_v2')
        # Relocate ONLY the frozen test module's two filesystem constants.
        module.REPO, module.EVID = REPO, HERE
        return module.run_case(folder)
    if kind == 'resource':
        module = load('test_binding_resources_v2_draft')
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromModule(module))
        assert result.wasSuccessful(), 'resource corpus failure'
        return {'unittest_methods': result.testsRun, 'fixed_subcontrols': 51}
    module = load('log_witness_dispatcher_draft')
    if kind == 'primitive':
        return module.run_primitive(case)
    if kind == 'reader':
        return module.run_reader_limit(folder)
    return module.run_case(case, folder)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def main():
    if sys.flags.optimize != 0:
        raise SystemExit('Refusing optimized Python: control assertions must remain active')
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', default='all')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', nargs=2, metavar=('KIND', 'CASE'))
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    if manifest['status'] != 'FROZEN_FOR_PORTABLE_COMPONENT_EXECUTION':
        raise SystemExit('DRAFT: independent review/freeze required; no controls executed')
    selected = sum(manifest['groups'].values(), []) if args.group == 'all' else manifest['groups'][args.group]
    if args.worker:
        assert args.worker in selected, 'unregistered case'
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'cases': [], 'scope': 'focused components, not CLI/full suite/original13 closure'}
    cache = args.output / 'absent-cache'
    try:
        assert not cache.exists()
        sys.dont_write_bytecode = True
        sys.pycache_prefix = str(cache)
        report['runtime_before'] = verify(manifest)
        if args.worker:
            assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
            report['result'] = invoke(*args.worker, args.output / 'fixture')
        else:
            for index, (kind, case) in enumerate(selected):
                verify(manifest)
                child = args.output / ('%03d-%s' % (index, case))
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                           PYTHONPYCACHEPREFIX=str(child / 'absent-cache'))
                env.pop('PYTHONOPTIMIZE', None)
                command = [sys.executable, '-B', str(Path(__file__).resolve()),
                           '--group', args.group, '--output', str(child), '--worker', kind, case]
                completed = subprocess.run(command, env=env, text=True, capture_output=True)
                (args.output / ('%03d.stdout' % index)).write_text(completed.stdout)
                (args.output / ('%03d.stderr' % index)).write_text(completed.stderr)
                report['cases'].append({'kind': kind, 'case': case, 'returncode': completed.returncode})
                assert completed.returncode == 0, 'case failed; no retry or further cases'
        report['status'] = 'PASS'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['traceback'] = traceback.format_exc()
    finally:
        try:
            report['runtime_after'] = verify(manifest)
            assert not cache.exists(), 'cache unexpectedly written'
        except BaseException as error:
            report['status'] = 'FAIL'
            report['final_check_error'] = type(error).__name__ + ': ' + str(error)
        save(args.output / 'RESULT.json', report)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
