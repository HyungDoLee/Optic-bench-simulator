"""Run the existing and 4f tests; persist per-test status and numerical errors.

Run from repository root: python tools/verify_4f.py --output reports
GUI tests require DISPLAY. --capture-dir saves real GUI screenshots if enabled.
The exit status is nonzero on failure; skipped GUI checks are never marked passed.
"""
import argparse
from datetime import datetime, timezone, timedelta
import io
import json
import numbers
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def json_scalar(value):
    """Matplotlib/NumPy measurements may carry scalar bool/int/float types."""
    import numpy as np
    if isinstance(value,np.generic):return value.item()
    raise TypeError(f'Unsupported report value: {type(value).__name__}')


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.records=[]
        self.current={}

    def startTest(self,test):
        super().startTest(test)
        self.current=dict(test=test.id(),status='running')
        # Observe existing numerical assertions without changing their tolerance
        # or replacing their verdict. New 4f tests already record measurements.
        if not hasattr(test,'measure'):
            test.measurements=[]
            for method in ('assertAlmostEqual','assertEqual','assertLess','assertLessEqual'):
                original=getattr(test,method)
                def observed(first,second,*args,_method=method,_original=original,**kwargs):
                    numeric=isinstance(first,numbers.Real) and isinstance(second,numbers.Real)
                    record=None
                    if numeric:
                        error=abs(first-second) if _method in ('assertAlmostEqual','assertEqual') else max(0.,first-second)
                        record=dict(name=_method,actual=first,expected=second,
                                    absolute_error=error,relative_error=None,passed=False,
                                    criterion=dict(assertion=_method,args=list(args),kwargs=kwargs))
                        test.measurements.append(record)
                    try:
                        answer=_original(first,second,*args,**kwargs)
                    except AssertionError:
                        raise
                    else:
                        if record is not None:record['passed']=True
                        return answer
                setattr(test,method,observed)

    def addSuccess(self,test):
        super().addSuccess(test)
        self.current['status']='passed'

    def addFailure(self,test,err):
        super().addFailure(test,err)
        self.current.update(status='failed',reason=self._exc_info_to_string(err,test))

    def addError(self,test,err):
        super().addError(test,err)
        self.current.update(status='error',reason=self._exc_info_to_string(err,test))

    def addSkip(self,test,reason):
        super().addSkip(test,reason)
        self.current.update(status='skipped',reason=reason)

    def stopTest(self,test):
        checks=getattr(test,'measurements',[])
        self.current['measurements']=checks
        self.current['max_absolute_error']=max((c['absolute_error'] for c in checks),default=None)
        self.records.append(self.current.copy())
        super().stopTest(test)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports')
    parser.add_argument('--capture-dir',type=Path)
    args=parser.parse_args()
    if args.capture_dir:os.environ['OPTICS_CAPTURE_DIR']=str(args.capture_dir.resolve())
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    print(log.getvalue(),end='')
    args.output.mkdir(parents=True,exist_ok=True)
    counts={name:sum(r['status']==name for r in result.records)
            for name in ('passed','failed','error','skipped')}
    generated=datetime.now(timezone(timedelta(hours=9),name='KST'))
    payload=dict(generated_at=generated.isoformat(),
                 python=sys.version.split()[0],counts=counts,tests=result.records)
    (args.output/'test_results.json').write_text(json.dumps(payload,indent=2,default=json_scalar),encoding='utf-8')
    lines=['# 720 nm 4f automated verification','',
           f'작성일: {generated:%Y-%m-%d}','',
           f'작성 시각: {generated:%H:%M:%S} KST (UTC+09:00)','',
           str(counts),'',
           'Errors are absolute differences in the measurement units. The maximum per test mixes units; see JSON for each measurement and tolerance.',
           'Existing regression assertions retain their original verdict/tolerance. Inequality error means constraint violation. N/A means the test has no scalar numerical comparison (e.g. JSON validation or list comparison).','',
           '| Test | Status | Max absolute error |','|---|---|---|']
    for row in result.records:
        error=row['max_absolute_error']
        lines.append(f"| {row['test']} | {row['status']} | {error:.6g} |" if error is not None
                     else f"| {row['test']} | {row['status']} | N/A |")
        if row.get('reason'):lines.extend(['','```',row['reason'],'```',''])
    (args.output/'test_results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (args.output/'unittest.log').write_text(log.getvalue(),encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':sys.exit(main())
