"""
웹 기반 GUI 인터페이스 모듈
- Flask를 사용한 브라우저 기반 GUI
- tkinter 대신 사용
"""

from flask import Flask, render_template_string, request, jsonify
import threading
import time
import random
import logging
import webbrowser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config_manager import ConfigManager
# Cloudflare 우회를 위해 Selenium 사용
try:
    from web_scraper_selenium import OncaPanScraperSelenium as OncaPanScraper
    USE_SELENIUM = True
    logger.info("Selenium 모드로 실행됩니다 (Cloudflare 우회)")
except ImportError as e:
    logger.warning(f"Selenium을 사용할 수 없습니다: {e}")
    logger.warning("requests 모드로 전환합니다 (Cloudflare 차단 가능)")
    from web_scraper import OncaPanScraper
    USE_SELENIUM = False
from ai_comment_generator import AICommentGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'oncapan_macro_secret_key'

# 전역 변수
config_manager = ConfigManager()
scraper = None
ai_generator = None
is_running = False
worker_thread = None
status_info = {
    'status': '대기 중',
    'log': [],
    'commented_count': 0
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>온카판 자동 댓글 매크로</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Malgun Gothic', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            padding: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        .section {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"],
        input[type="password"],
        input[type="number"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 10px;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .log-area {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            height: 300px;
            overflow-y: auto;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            margin-top: 20px;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 3px 0;
        }
        .status-bar {
            background: #28a745;
            color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
            margin-top: 20px;
        }
        .status-bar.stopped {
            background: #6c757d;
        }
        .status-bar.running {
            background: #28a745;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎰 온카판 자동 댓글 매크로</h1>
        
        <form id="configForm">
            <div class="section">
                <h2>로그인 정보</h2>
                <div class="form-group">
                    <label>아이디:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label>비밀번호:</label>
                    <input type="password" id="password" name="password" required>
                </div>
            </div>
            
            <div class="section">
                <h2>OpenAI API 설정</h2>
                <div class="form-group">
                    <label>API 키:</label>
                    <input type="password" id="api_key" name="api_key" required>
                </div>
            </div>
            
            <div class="section">
                <h2>댓글 작성 시간 설정</h2>
                <div class="form-group">
                    <label>게시글 접속 후 대기 시간 (초):</label>
                    <input type="number" id="delay" name="delay" value="10" min="1" required>
                </div>
                <div class="form-group">
                    <label>최소 대기 시간 (초):</label>
                    <input type="number" id="min_delay" name="min_delay" value="5" min="1" required>
                </div>
                <div class="form-group">
                    <label>최대 대기 시간 (초):</label>
                    <input type="number" id="max_delay" name="max_delay" value="15" min="1" required>
                </div>
            </div>
            
        <div class="section">
            <div class="checkbox-group">
                <input type="checkbox" id="test_mode" name="test_mode">
                <label for="test_mode">테스트 모드 (실제 댓글 작성 안 함)</label>
            </div>
        </div>
        
        <div class="section">
            <h2>댓글 학습 데이터</h2>
            <div class="form-group">
                <label>수집된 댓글 수:</label>
                <span id="collected_count">0개</span>
            </div>
            <div class="checkbox-group" style="margin: 10px 0;">
                <input type="checkbox" id="auto_collect" name="auto_collect">
                <label for="auto_collect">매크로 시작 시 댓글이 없으면 자동 수집</label>
            </div>
            <button type="button" class="btn-primary" onclick="collectComments()" style="width: 100%; margin-top: 10px;">댓글 수집하기 (수동)</button>
            <p style="font-size: 12px; color: #666; margin-top: 10px;">
                <strong>📚 실시간 학습 모드 (테스트 모드에서 자동 활성화):</strong><br>
                • 게시글 처리 시 자동으로 실제 댓글 수집<br>
                • 수집한 댓글을 즉시 학습 데이터에 추가<br>
                • 게시글 본문, 실제 댓글, AI 댓글을 로그 파일에 기록<br>
                • <code>learning_log.txt</code> 파일에서 상세 내용 확인 가능
            </p>
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                <strong>일반 학습 방식:</strong><br>
                • 댓글 수집: 처음 한 번은 수동으로 실행 (또는 자동 수집 옵션 사용)<br>
                • 댓글 생성: 수집된 댓글을 자동으로 학습에 활용<br>
                • 권장: 최소 50개 이상의 댓글 수집
            </p>
        </div>
            
            <div class="button-group">
                <button type="button" class="btn-primary" onclick="saveConfig()">설정 저장</button>
                <button type="button" class="btn-success" onclick="startMacro()" id="startBtn">시작</button>
                <button type="button" class="btn-danger" onclick="stopMacro()" id="stopBtn" disabled>중지</button>
            </div>
        </form>
        
        <div class="status-bar" id="statusBar">대기 중...</div>
        
        <div class="section">
            <h2>실행 로그</h2>
            <div class="log-area" id="logArea"></div>
        </div>
    </div>
    
    <script>
        let updateInterval;
        
        function addLog(message) {
            const logArea = document.getElementById('logArea');
            const timestamp = new Date().toLocaleTimeString('ko-KR');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `[${timestamp}] ${message}`;
            logArea.appendChild(entry);
            logArea.scrollTop = logArea.scrollHeight;
        }
        
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('statusBar').textContent = data.status;
                    document.getElementById('statusBar').className = 'status-bar ' + (data.status.includes('실행') ? 'running' : 'stopped');
                    
                    if (data.log && data.log.length > 0) {
                        const logArea = document.getElementById('logArea');
                        const currentLogs = logArea.children.length;
                        data.log.slice(currentLogs).forEach(log => {
                            addLog(log);
                        });
                    }
                    
                    if (data.is_running) {
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('stopBtn').disabled = false;
                    } else {
                        document.getElementById('startBtn').disabled = false;
                        document.getElementById('stopBtn').disabled = true;
                    }
                })
                .catch(err => console.error('Status update error:', err));
        }
        
        function saveConfig() {
            const formData = new FormData(document.getElementById('configForm'));
            fetch('/save_config', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    addLog('설정이 저장되었습니다.');
                }
            });
        }
        
        function startMacro() {
            const formData = new FormData(document.getElementById('configForm'));
            fetch('/start', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLog('매크로를 시작합니다...');
                    updateInterval = setInterval(updateStatus, 1000);
                } else {
                    alert(data.message);
                }
            });
        }
        
        function stopMacro() {
            fetch('/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addLog('매크로를 중지합니다...');
                        clearInterval(updateInterval);
                        updateStatus();
                    }
                });
        }
        
        function collectComments() {
            if (confirm('댓글 수집을 시작합니다. 몇 분이 걸릴 수 있습니다. 계속하시겠습니까?')) {
                addLog('댓글 수집 시작...');
                fetch('/collect_comments', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            addLog(`댓글 수집 완료: ${data.count}개 수집`);
                            updateCollectedCount();
                        } else {
                            addLog(`댓글 수집 실패: ${data.message}`);
                        }
                    });
            }
        }
        
        function updateCollectedCount() {
            fetch('/comment_count')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('collected_count').textContent = `${data.count}개`;
                });
        }
        
        // 페이지 로드 시 설정 불러오기 및 상태 업데이트 시작
        window.onload = function() {
            fetch('/load_config')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.config) {
                        document.getElementById('username').value = data.config.username || '';
                        document.getElementById('api_key').value = data.config.api_key || '';
                        document.getElementById('delay').value = data.config.comment_delay || 10;
                        document.getElementById('min_delay').value = data.config.min_delay || 5;
                        document.getElementById('max_delay').value = data.config.max_delay || 15;
                        addLog('저장된 설정을 불러왔습니다.');
                    }
                });
            
            updateCollectedCount();
            updateStatus();
            setInterval(updateStatus, 2000);
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/save_config', methods=['POST'])
def save_config():
    global config_manager
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        api_key = request.form.get('api_key')
        delay = int(request.form.get('delay', 10))
        min_delay = int(request.form.get('min_delay', 5))
        max_delay = int(request.form.get('max_delay', 15))
        
        if not username or not password or not api_key:
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'})
        
        if min_delay >= max_delay:
            return jsonify({'success': False, 'message': '최소 대기 시간은 최대 대기 시간보다 작아야 합니다.'})
        
        auto_collect = request.form.get('auto_collect') == 'on'
        config_manager.save_config(username, password, api_key, delay, min_delay, max_delay, auto_collect=auto_collect)
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

@app.route('/load_config', methods=['GET'])
def load_config():
    global config_manager
    try:
        config = config_manager.load_config()
        if config:
            # 비밀번호는 보안상 전송하지 않음
            return jsonify({
                'success': True,
                'config': {
                    'username': config.get('username', ''),
                    'api_key': config.get('api_key', ''),
                    'comment_delay': config.get('comment_delay', 10),
                    'min_delay': config.get('min_delay', 5),
                    'max_delay': config.get('max_delay', 15),
                    'auto_collect': config.get('auto_collect', False)
                }
            })
        return jsonify({'success': False, 'config': None})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/start', methods=['POST'])
def start():
    global is_running, worker_thread, scraper, ai_generator, status_info
    
    if is_running:
        return jsonify({'success': False, 'message': '이미 실행 중입니다.'})
    
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        api_key = request.form.get('api_key')
        delay = int(request.form.get('delay', 10))
        min_delay = int(request.form.get('min_delay', 5))
        max_delay = int(request.form.get('max_delay', 15))
        test_mode = request.form.get('test_mode') == 'on'
        auto_collect = request.form.get('auto_collect') == 'on'
        
        if not username or not password or not api_key:
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'})
        
        # 자동 수집 옵션이 켜져 있고 댓글이 없으면 자동 수집
        if auto_collect:
            import os
            import json
            comments_file = "collected_comments.json"
            if not os.path.exists(comments_file):
                add_log('댓글이 없어 자동으로 댓글을 수집합니다...')
                try:
                    from comment_collector import CommentCollector
                    collector = CommentCollector()
                    # 로그인 필요하므로 스킵하고 경고만
                    add_log('⚠️ 자동 수집은 로그인 후 수동으로 실행해주세요.')
                except:
                    pass
        
        is_running = True
        status_info['status'] = '실행 중...'
        status_info['log'] = []
        status_info['commented_count'] = 0
        
        worker_thread = threading.Thread(
            target=macro_worker,
            args=(username, password, api_key, delay, min_delay, max_delay, test_mode),
            daemon=True
        )
        worker_thread.start()
        
        return jsonify({'success': True, 'message': '매크로를 시작했습니다.'})
    except Exception as e:
        is_running = False
        return jsonify({'success': False, 'message': f'오류: {str(e)}'})

@app.route('/stop', methods=['POST'])
def stop():
    global is_running, scraper, status_info
    
    is_running = False
    if scraper:
        scraper.close()
    
    status_info['status'] = '중지됨'
    add_log('매크로를 중지합니다...')
    
    return jsonify({'success': True, 'message': '매크로를 중지했습니다.'})

@app.route('/status', methods=['GET'])
def status():
    global is_running, status_info
    return jsonify({
        'is_running': is_running,
        'status': status_info['status'],
        'log': status_info['log'][-50:],  # 최근 50개만
        'commented_count': status_info['commented_count']
    })

@app.route('/collect_comments', methods=['POST'])
def collect_comments():
    """댓글 수집"""
    try:
        from comment_collector import CommentCollector
        
        collector = CommentCollector()
        comments = collector.collect_comments_from_board(limit_posts=10, comments_per_post=10)
        saved_count = collector.save_comments(comments)
        collector.analyze_comments()
        collector.close()
        
        # AI 생성기는 필요할 때마다 댓글을 로드하므로 재초기화 불필요
        # (최신 데이터를 항상 반영)
        
        return jsonify({'success': True, 'count': saved_count})
    except Exception as e:
        logger.error(f"댓글 수집 오류: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/comment_count', methods=['GET'])
def comment_count():
    """수집된 댓글 수 확인"""
    try:
        import os
        import json
        comments_file = "collected_comments.json"
        if os.path.exists(comments_file):
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
                return jsonify({'count': len(comments)})
        return jsonify({'count': 0})
    except:
        return jsonify({'count': 0})

def add_log(message):
    global status_info
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    status_info['log'].append(log_entry)
    if len(status_info['log']) > 1000:  # 로그 제한
        status_info['log'] = status_info['log'][-1000:]

def macro_worker(username, password, api_key, delay, min_delay, max_delay, test_mode):
    global is_running, scraper, ai_generator, status_info
    max_retries = 3
    retry_count = 0
    
    # 실시간 학습 모듈 초기화
    from realtime_learner import RealtimeLearner
    learner = RealtimeLearner()
    
    while is_running and retry_count < max_retries:
        try:
            scraper = OncaPanScraper(test_mode=test_mode)
            ai_generator = AICommentGenerator(api_key)
            
            if test_mode:
                add_log("⚠️ 테스트 모드로 실행됩니다. 실제 댓글은 작성되지 않습니다.")
                add_log("📚 실시간 학습 모드: 게시글과 댓글을 자동으로 수집하여 학습합니다.")
            
            add_log("로그인 시도 중...")
            if not scraper.login(username, password):
                retry_count += 1
                if retry_count < max_retries:
                    add_log(f"로그인 실패. 재시도 중... ({retry_count}/{max_retries})")
                    time.sleep(5)
                    continue
                else:
                    add_log("로그인 실패. 매크로를 중지합니다.")
                    is_running = False
                    status_info['status'] = '로그인 실패'
                    return
            
            add_log("로그인 성공!")
            retry_count = 0
            commented_posts = set()
            
            while is_running:
                try:
                    add_log("게시글 목록을 가져오는 중...")
                    posts = scraper.get_post_list(limit=20)
                    
                    if not posts:
                        add_log("게시글을 찾을 수 없습니다. 잠시 후 재시도...")
                        time.sleep(30)
                        continue
                    
                    for post in posts:
                        if not is_running:
                            break
                        
                        post_id = post.get('id')
                        post_url = post.get('url')
                        
                        if not post_id or not post_url:
                            continue
                        
                        if post_id in commented_posts:
                            continue
                        
                        if scraper.has_commented(post_url, username):
                            commented_posts.add(post_id)
                            add_log(f"이미 댓글을 단 게시글: {post.get('title', '')[:30]}")
                            continue
                        
                        post_title = post.get('title', '')[:30]
                        add_log(f"게시글 처리 중: {post_title}")
                        post_data = scraper.get_post_content(post_url)
                        
                        if not post_data:
                            continue
                        
                        post_content = post_data.get('content', '')
                        
                        # 실시간 학습: 게시글에서 댓글 수집
                        add_log("📖 게시글의 실제 댓글 수집 중...")
                        actual_comments = learner.collect_comments_from_post(scraper, post_url)
                        
                        if actual_comments:
                            add_log(f"✅ {len(actual_comments)}개의 실제 댓글을 수집했습니다.")
                            # 수집한 댓글을 학습 데이터에 추가
                            new_count = learner.save_comments_to_learning_data(actual_comments)
                            if new_count > 0:
                                add_log(f"📚 새로운 댓글 {new_count}개를 학습 데이터에 추가했습니다.")
                                # AI 생성기를 다시 초기화하여 새로운 댓글 반영
                                ai_generator = AICommentGenerator(api_key)
                        else:
                            add_log("⚠️ 이 게시글에는 댓글이 없습니다.")
                        
                        if not ai_generator.can_generate_comment(post_content):
                            add_log("댓글 생성 불가능한 게시글입니다. 건너뜁니다.")
                            # 그래도 로그는 기록
                            learner.log_post_processing(
                                post.get('title', ''),
                                post_content,
                                actual_comments,
                                None,
                                post_url
                            )
                            continue
                        
                        wait_time = random.uniform(min_delay, max_delay)
                        add_log(f"{wait_time:.1f}초 대기 중...")
                        time.sleep(wait_time)
                        
                        add_log("🤖 AI 댓글 생성 중... (수집된 댓글을 참고하여 생성)")
                        comment = ai_generator.generate_comment(post_content, post.get('title', ''))
                        
                        if not comment:
                            add_log("댓글 생성 실패. 건너뜁니다.")
                            # 로그는 기록
                            learner.log_post_processing(
                                post.get('title', ''),
                                post_content,
                                actual_comments,
                                None,
                                post_url
                            )
                            continue
                        
                        add_log(f"생성된 댓글: {comment}")
                        
                        # 상세 로그 기록
                        learner.log_post_processing(
                            post.get('title', ''),
                            post_content,
                            actual_comments,
                            comment,
                            post_url
                        )
                        learner.add_processed_post({
                            'title': post.get('title', ''),
                            'content': post_content,
                            'url': post_url,
                            'actual_comments': actual_comments,
                            'ai_comment': comment
                        })
                        
                        # 학습 요약 출력
                        summary = learner.get_learning_summary()
                        add_log(f"📊 학습 현황: 처리 게시글 {summary['processed_posts']}개, 학습 댓글 {summary['total_learned_comments']}개")
                        
                        if not test_mode:
                            if scraper.write_comment(post_url, comment):
                                commented_posts.add(post_id)
                                status_info['commented_count'] = len(commented_posts)
                                add_log("댓글 작성 완료!")
                                status_info['status'] = f"댓글 작성 완료: {len(commented_posts)}개"
                            else:
                                add_log("댓글 작성 실패.")
                        else:
                            add_log("[테스트 모드] 댓글 작성 시뮬레이션 완료")
                            commented_posts.add(post_id)
                            status_info['commented_count'] = len(commented_posts)
                            status_info['status'] = f"테스트 완료: {len(commented_posts)}개"
                        
                        time.sleep(delay)
                    
                    add_log("다음 게시글 목록을 기다리는 중...")
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"게시글 처리 오류: {e}", exc_info=True)
                    add_log(f"오류 발생: {str(e)}")
                    time.sleep(10)
                    continue
            
        except Exception as e:
            logger.error(f"매크로 작업 오류: {e}", exc_info=True)
            add_log(f"심각한 오류 발생: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                add_log(f"재시도 중... ({retry_count}/{max_retries})")
                time.sleep(10)
            else:
                add_log("최대 재시도 횟수 초과. 매크로를 중지합니다.")
                is_running = False
                status_info['status'] = '오류로 인한 중지'
                break
        finally:
            # 최종 학습 요약
            if 'learner' in locals():
                summary = learner.get_learning_summary()
                add_log(f"\n📚 최종 학습 요약:")
                add_log(f"  - 처리한 게시글: {summary['processed_posts']}개")
                add_log(f"  - 학습한 댓글: {summary['total_learned_comments']}개")
                add_log(f"  - 상세 로그: {learner.log_file} 파일을 확인하세요.")
            
            if scraper:
                scraper.close()
            
            is_running = False
            status_info['status'] = '중지됨'

def run_web_gui(port=5000):
    """웹 GUI 실행"""
    # Werkzeug 로그 숨기기
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # ERROR 레벨만 표시
    
    url = f'http://localhost:{port}'
    print(f"\n{'='*60}")
    print("웹 GUI가 시작되었습니다!")
    print(f"{'='*60}")
    print(f"\n브라우저에서 다음 주소로 접속하세요:")
    print(f"  {url}")
    print(f"\n브라우저가 자동으로 열립니다...")
    print(f"\n종료하려면 Ctrl+C를 누르세요.")
    print(f"{'='*60}\n")
    
    # 1초 후 브라우저 자동 열기
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_web_gui()

