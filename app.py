"""
Chess Game Web Application
支持本地运行的国际象棋游戏，带LLM评论功能
"""
from flask import Flask, render_template, request, jsonify

import chess
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import ChessEngine, get_engine
from llm import LLMClient, get_llm

app = Flask(__name__, 
            static_folder='static',
            template_folder='static')

# 简单CORS处理（替代flask_cors）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# 全局状态
games = {}  # 存储多个游戏实例

class GameSession:
    """游戏会话1"""
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.board = chess.Board()
        self.engine = None
        self.llm = None
        self.player_color = chess.WHITE  # 玩家执白棋
        self.difficulty = 2  # 中等难度
        self.move_history = []
        self.evaluations = []
    
    def setup_engine(self, difficulty: int, stockfish_path: str = None):
        """设置引擎难度"""
        self.difficulty = difficulty
        self.engine = ChessEngine(difficulty, stockfish_path)
    
    def setup_llm(self, backend: str, base_url: str = None, model: str = None):
        """设置LLM"""
        # backend=none 表示彻底禁用评论（不生成任何点评，包括规则兜底）
        if backend == "none":
            self.llm = None
            return
        self.llm = LLMClient(backend, base_url, model)
    
    def reset(self):
        """重置游戏"""
        self.board = chess.Board()
        self.move_history = []
        self.evaluations = []

def get_or_create_game(game_id: str) -> GameSession:
    """获取或创建游戏会话"""
    if game_id not in games:
        games[game_id] = GameSession(game_id)
    return games[game_id]

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """创建新游戏"""
    data = request.json or {}
    game_id = data.get('game_id', 'default')
    difficulty = data.get('difficulty', 2)
    player_color = data.get('player_color', 'white')
    
    game = get_or_create_game(game_id)
    game.reset()
    game.setup_engine(difficulty)
    
    if player_color == 'white':
        game.player_color = chess.WHITE
    else:
        game.player_color = chess.BLACK
    
    return jsonify({
        'success': True,
        'game_id': game_id,
        'fen': game.board.fen(),
        'turn': 'white' if game.board.turn == chess.WHITE else 'black',
        'player_color': player_color
    })

@app.route('/api/get_state', methods=['GET'])
def get_state():
    """获取游戏状态"""
    game_id = request.args.get('game_id', 'default')
    game = get_or_create_game(game_id)
    
    turn = 'white' if game.board.turn == chess.WHITE else 'black'
    
    return jsonify({
        'success': True,
        'fen': game.board.fen(),
        'turn': turn,
        'is_check': game.board.is_check(),
        'is_checkmate': game.board.is_checkmate(),
        'is_stalemate': game.board.is_stalemate(),
        'is_game_over': game.board.is_game_over(),
        'move_history': game.move_history,
        'difficulty': game.difficulty
    })

@app.route('/api/make_move', methods=['POST'])
def make_move():
    """执行玩家走棋"""
    data = request.json
    game_id = data.get('game_id', 'default')
    move_uci = data.get('move')  # UCI 格式，如 "e2e4"
    
    game = get_or_create_game(game_id)
    
    try:
        # 解析着法
        move = chess.Move.from_uci(move_uci)
        
        if move not in game.board.legal_moves:
            return jsonify({
                'success': False,
                'error': '非法着法'
            })
        
        # 走棋前分析
        analysis = game.engine.get_move_analysis(game.board, move) if game.engine else None

        # 计算 SAN 必须在 push 之前进行。
        # python-chess 的 san()/lan() 要求传入的 move 在“当前局面”是合法的，
        # 先 push 会导致断言失败。
        san = game.board.san(move)
        
        # 执行着法
        game.board.push(move)
        game.move_history.append({
            'san': san if game.move_history else move_uci,
            'uci': move_uci
        })
        
        # 保存评估
        if analysis:
            game.evaluations.append(analysis)
        
        # 检查游戏结束
        game_over = game.board.is_game_over()
        checkmate = game.board.is_checkmate()
        
        # LLM 评论
        commentary = ""
        if game.llm and analysis:
            commentary = game.llm.analyze_move(analysis)
        
        response = {
            'success': True,
            'fen': game.board.fen(),
            'turn': 'white' if game.board.turn == chess.WHITE else 'black',
            'is_check': game.board.is_check(),
            'is_checkmate': checkmate,
            'is_game_over': game_over,
            'last_move': move_uci,
            'analysis': analysis,
            'commentary': commentary
        }
        
        return jsonify(response)
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'无效着法: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/ai_move', methods=['POST'])
def ai_move():
    """AI走棋"""
    data = request.json or {}
    game_id = data.get('game_id', 'default')
    
    game = get_or_create_game(game_id)
    
    if game.board.is_game_over():
        return jsonify({
            'success': False,
            'error': '游戏已结束'
        })
    
    if not game.engine:
        game.setup_engine(game.difficulty)
    
    # AI 计算着法
    ai_move = game.engine.get_best_move(game.board)
    
    if not ai_move:
        return jsonify({
            'success': False,
            'error': '引擎无法计算着法'
        })
    
    # 走棋前分析
    analysis = game.engine.get_move_analysis(game.board, ai_move)

    # 同样：SAN 必须在 push 之前计算
    san = game.board.san(ai_move)
    
    # 执行着法
    game.board.push(ai_move)
    game.move_history.append({
        'san': san if game.move_history else ai_move.uci(),
        'uci': ai_move.uci()
    })
    
    # 保存评估
    if analysis:
        game.evaluations.append(analysis)
    
    # LLM 评论
    commentary = ""
    if game.llm and analysis:
        commentary = game.llm.analyze_move(analysis)
    
    response = {
        'success': True,
        'fen': game.board.fen(),
        'turn': 'white' if game.board.turn == chess.WHITE else 'black',
        'move': ai_move.uci(),
        'is_check': game.board.is_check(),
        'is_checkmate': game.board.is_checkmate(),
        'is_game_over': game.board.is_game_over(),
        'analysis': analysis,
        'commentary': commentary
    }
    
    return jsonify(response)

@app.route('/api/set_difficulty', methods=['POST'])
def set_difficulty():
    """设置难度"""
    data = request.json
    game_id = data.get('game_id', 'default')
    difficulty = data.get('difficulty', 2)
    
    game = get_or_create_game(game_id)
    game.difficulty = difficulty
    if game.engine:
        game.engine.set_difficulty(difficulty)
    
    return jsonify({
        'success': True,
        'difficulty': difficulty,
        'difficulty_name': ['', '简单', '中等', '困难'][difficulty]
    })

@app.route('/api/configure_llm', methods=['POST'])
def configure_llm():
    """配置LLM"""
    data = request.json
    game_id = data.get('game_id', 'default')
    backend = data.get('backend', 'none')  # none, ollama, opencode
    base_url = data.get('base_url')
    model = data.get('model')
    
    game = get_or_create_game(game_id)
    game.setup_llm(backend, base_url, model)
    
    return jsonify({
        'success': True,
        'backend': backend,
        'available': game.llm.available if game.llm else False
    })

@app.route('/api/evaluate', methods=['GET'])
def evaluate():
    """评估当前局面"""
    game_id = request.args.get('game_id', 'default')
    game = get_or_create_game(game_id)
    
    if not game.engine:
        game.setup_engine(game.difficulty)
    
    eval_score, white_prob, black_prob = game.engine.evaluate_position(game.board)
    
    return jsonify({
        'success': True,
        'eval_score': eval_score,
        'white_win_prob': white_prob,
        'black_win_prob': black_prob,
        'is_check': game.board.is_check(),
        'is_checkmate': game.board.is_checkmate()
    })

@app.route('/api/legal_moves', methods=['GET'])
def legal_moves():
    """获取合法着法列表"""
    game_id = request.args.get('game_id', 'default')
    game = get_or_create_game(game_id)
    
    moves = [move.uci() for move in game.board.legal_moves]
    
    return jsonify({
        'success': True,
        'legal_moves': moves
    })

@app.route('/api/undo', methods=['POST'])
def undo():
    """悔棋"""
    data = request.json or {}
    game_id = data.get('game_id', 'default')
    moves_to_undo = data.get('moves', 2)  # 默认悔两步（玩家和AI各一步）
    
    game = get_or_create_game(game_id)
    
    for _ in range(min(moves_to_undo, len(game.board.move_stack))):
        game.board.pop()
        if game.move_history:
            game.move_history.pop()
        if game.evaluations:
            game.evaluations.pop()
    
    return jsonify({
        'success': True,
        'fen': game.board.fen(),
        'turn': 'white' if game.board.turn == chess.WHITE else 'black'
    })

# 检查 Stockfish
def check_stockfish():
    """检查系统是否安装了 Stockfish"""
    import shutil
    stockfish_path = shutil.which('stockfish')
    if stockfish_path:
        print(f"✓ 找到 Stockfish: {stockfish_path}")
        return stockfish_path
    else:
        print("✗ 未找到 Stockfish，将使用内置AI")
        return None

if __name__ == '__main__':
    print("=" * 50)
    print("国际象棋对战平台 v1.0")
    print("=" * 50)
    
    stockfish_path = check_stockfish()
    
    print("\n启动服务器...")
    print("访问地址: http://localhost:5001")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)