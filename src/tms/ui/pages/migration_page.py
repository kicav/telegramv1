from __future__ import annotations
from datetime import datetime,timezone
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QProgressBar,QPushButton,QVBoxLayout,QWidget
from ..controllers.migration_controller import MigrationController
from ..widgets.filter_panel import FilterPanel

class MigrationPage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);self.ctx=ctx;self.controller=MigrationController(ctx.commands);self.current_job_id=None;self._checking=False;self._check_account=None;self._check_dataset=None;self._waiting_until=None
        layout=QVBoxLayout(self);title=QLabel('THAO TÁC THÀNH VIÊN');title.setStyleSheet('font-size:20px;font-weight:600');layout.addWidget(title)
        form=QFormLayout();self.account=QComboBox();self.dataset=QComboBox();self.target_reference=QLineEdit();self.target_reference.setPlaceholderText('Link group đích hoặc @username');self.action=QComboBox();self.action.addItem('Thêm thành viên','INVITE');self.action.addItem('Xóa thành viên','REMOVE');self.speed=QComboBox();self.speed.addItem('Nhanh — 3 giây',3.0);self.speed.addItem('Tiêu chuẩn — 5 giây',5.0);self.speed.addItem('Thận trọng — 8 giây',8.0);self.speed.setCurrentIndex(1)
        for label,w in [('Tài khoản',self.account),('Nguồn member',self.dataset),('Group đích',self.target_reference),('Thao tác',self.action),('Tốc độ mục tiêu',self.speed)]:form.addRow(label,w)
        layout.addLayout(form);self.filters=FilterPanel();layout.addWidget(self.filters)
        row=QHBoxLayout();self.refresh=QPushButton('Làm mới');self.check=QPushButton('KIỂM TRA');self.start=QPushButton('BẮT ĐẦU');self.pause=QPushButton('Tạm dừng');self.resume=QPushButton('Tiếp tục');self.stop=QPushButton('Dừng');
        for b in (self.refresh,self.check,self.start,self.pause,self.resume,self.stop):row.addWidget(b)
        layout.addLayout(row);self.summary=QLabel('Chọn dữ liệu và group đích, sau đó bấm KIỂM TRA.');self.status=QLabel('Trạng thái: Sẵn sàng');self.progress=QProgressBar();self.counters=QLabel('Thành công 0   Bỏ qua 0   Lỗi 0   Đã xử lý 0');self.next_attempt=QLabel('Lần xử lý tiếp: —');layout.addWidget(self.summary);layout.addWidget(self.progress);layout.addWidget(self.counters);layout.addWidget(self.status);layout.addWidget(self.next_attempt);layout.addStretch()
        self.refresh.clicked.connect(self.refresh_sources);self.check.clicked.connect(self._check);self.start.clicked.connect(self._start);self.pause.clicked.connect(self._pause);self.resume.clicked.connect(self._resume);self.stop.clicked.connect(self._stop);self.timer=QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self._tick);self.timer.start();self.refresh_sources()
    def _safe(self,fn):
        try:fn()
        except Exception as exc:QMessageBox.warning(self,'Telegram Migration Studio',str(exc))
    def refresh_sources(self):
        a=self.account.currentData();d=self.dataset.currentData();self.account.clear();self.dataset.clear()
        for x in self.ctx.accounts.list_all():
            if x.id is not None and x.enabled:self.account.addItem(f'{x.phone} — {x.status}',x.id)
        for x in self.ctx.datasets.list_all():
            if x.id is not None:self.dataset.addItem(f'{x.name} ({x.member_count})',x.id)
        if a is not None and self.account.findData(a)>=0:self.account.setCurrentIndex(self.account.findData(a))
        if d is not None and self.dataset.findData(d)>=0:self.dataset.setCurrentIndex(self.dataset.findData(d))
    def _account_id(self):return int(self.account.currentData()) if self.account.currentData() is not None else None
    def _dataset_id(self):return int(self.dataset.currentData()) if self.dataset.currentData() is not None else None
    def _interval(self):return float(self.speed.currentData() or 5.0)
    def _check(self):
        account=self._account_id();dataset=self._dataset_id();ref=self.target_reference.text().strip()
        if account is None or dataset is None or not ref:QMessageBox.information(self,'Kiểm tra','Hãy chọn tài khoản, nguồn member và nhập group đích.');return
        self._checking=True;self._check_account=account;self._check_dataset=dataset;self.current_job_id=None;self.summary.setText('Đang kiểm tra group đích...');self._safe(lambda:self.controller.resolve_target(account,ref))
    def _start(self):
        account=self._account_id()
        if self.current_job_id is None or account is None:QMessageBox.information(self,'Bắt đầu','Hãy bấm KIỂM TRA và tạo kế hoạch trước.');return
        self._safe(lambda:self.controller.start(self.current_job_id,account,self._interval()))
    def _pause(self):
        if self.current_job_id is not None:self._safe(lambda:self.controller.pause(self.current_job_id))
    def _resume(self):
        if self.current_job_id is not None:self._safe(lambda:self.controller.resume(self.current_job_id,self._interval()))
    def _stop(self):
        if self.current_job_id is not None:self._safe(lambda:self.controller.stop(self.current_job_id))
    def _refresh_counters(self,job_id):
        s=self.ctx.jobs.summary(job_id);total=max(1,s['total']);self.progress.setValue(int(s['processed']*100/total));self.counters.setText(f"Thành công {s['success']}   Bỏ qua {s['skipped']}   Lỗi {s['failed']}   Đã xử lý {s['processed']}/{s['total']}")
    def _tick(self):
        if self._waiting_until is None:return
        try:dt=datetime.fromisoformat(self._waiting_until);dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc);left=max(0,int((dt-datetime.now(timezone.utc)).total_seconds()))
        except Exception:self._waiting_until=None;return
        self.next_attempt.setText(f'Lần xử lý tiếp: {left//60:02d}:{left%60:02d}')
        if left<=0:self._waiting_until=None
    def handle_event(self,event):
        if event.name in {'AccountsChanged','AccountStateChanged','DatasetCreated','ImportCompleted','MemberScanCompleted'}:self.refresh_sources()
        elif event.name=='TargetGroupResolved' and self._checking:
            g=event.payload['group'];self.summary.setText(f'Group: {g.title} | {g.type}. Đang kiểm tra quyền và thành viên...');self._safe(lambda:self.controller.precheck(self._check_account))
        elif event.name=='TargetPrecheckCompleted' and self._checking:
            self.summary.setText('Đang tạo kế hoạch xử lý...');self._safe(lambda:self.controller.plan(self._check_account,self._check_dataset,self.filters.spec(),str(self.action.currentData())))
        elif event.name=='MigrationPlanReady':
            self._checking=False;self.current_job_id=int(event.payload['job_id']);s=event.payload['summary'];action=event.payload.get('action','INVITE');verb='Thêm' if action=='INVITE' else 'Xóa';self.summary.setText(f'{verb}: nguồn {s.total_source} | đã có/không thuộc đích {s.already_target} | không hợp lệ {s.invalid} | có thể xử lý {s.ready} | Job #{self.current_job_id}');self._refresh_counters(self.current_job_id);self.status.setText('Trạng thái: Sẵn sàng bắt đầu')
        elif event.name=='JobStateChanged':
            jid=event.payload.get('job_id')
            if jid is not None and (self.current_job_id is None or int(jid)==self.current_job_id):
                self.current_job_id=int(jid);state=str(event.payload.get('state',''));self.status.setText('Trạng thái: '+({'RUNNING':'Đang xử lý','WAITING_SERVER':'Đang chờ Telegram','RATE_LIMITED':'Telegram đang giới hạn tài khoản','PAUSED':'Đã tạm dừng','COMPLETED':'Hoàn tất','COMPLETED_WITH_ERRORS':'Hoàn tất có lỗi','FAILED':'Lỗi'}.get(state,state)));self._waiting_until=event.payload.get('waiting_until');self._refresh_counters(self.current_job_id)
        elif event.name in {'MigrationItemCompleted','MigrationCompleted'}:
            jid=event.payload.get('job_id')
            if jid is not None:self.current_job_id=int(jid);self._refresh_counters(self.current_job_id)
