"""Stage progress and honest timing estimates, independent of Tk and physics."""
from dataclasses import dataclass
import math


def duration(seconds):
    seconds=max(0.,seconds)
    if seconds<60:return f'{seconds:.1f}초'
    minutes,remainder=divmod(int(seconds),60)
    return f'{minutes}분 {remainder:02d}초'


@dataclass
class WaveProgress:
    state: str = 'idle'
    fraction: float = 0.
    stage: str = '계산하기를 누르면 진행 상태를 표시합니다.'
    started_at: float | None = None
    finished_at: float | None = None
    previous_seconds: float | None = None

    def begin(self,now,previous_seconds=None):
        self.state='running';self.fraction=0.;self.stage='입력 설정 준비'
        self.started_at=now;self.finished_at=None;self.previous_seconds=previous_seconds

    def advance(self,fraction,stage):
        if self.state!='running' or not math.isfinite(fraction):return
        fraction=min(.99,max(0.,fraction))
        if fraction>=self.fraction:self.fraction=fraction;self.stage=stage

    def request_cancel(self):
        if self.state=='running':self.state='cancelling';self.stage='취소 요청 · 현재 연산이 끝나면 중단합니다.'

    def finish(self,now,state):
        self.finished_at=now;self.state=state
        if state=='succeeded':self.fraction=1.;self.stage='계산 완료'
        elif state=='cancelled':self.stage='계산 취소됨'
        else:self.stage='계산 실패 · 설정과 오류 메시지를 확인하세요.'

    def elapsed(self,now):
        if self.started_at is None:return 0.
        return max(0.,(self.finished_at if self.finished_at is not None else now)-self.started_at)

    def labels(self,now):
        elapsed=self.elapsed(now)
        if self.state=='idle':return self.stage,'경과 0.0초 · 예상 시간은 계산 기록이 생기면 표시합니다.'
        stage=f'단계 진행 {self.fraction*100:.0f}% · {self.stage}'
        if self.state not in ('running','cancelling'):return stage,f'총 경과 {duration(elapsed)}'
        if self.state=='cancelling':return stage,f'경과 {duration(elapsed)} · 취소 대기 중'
        if self.previous_seconds is None:return stage,f'경과 {duration(elapsed)} · 첫 계산: 예상 시간 측정 중'
        remaining=self.previous_seconds-elapsed
        if remaining<=0:return stage,f'경과 {duration(elapsed)} · 이전 계산보다 오래 걸리는 중'
        return stage,f'경과 {duration(elapsed)} · 예상 남은 시간 약 {duration(remaining)} (이전 동일 설정 기준)'
