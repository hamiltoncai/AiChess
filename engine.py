"""
Chess Engine Wrapper
支持 Stockfish 引擎和纯 Python AI
"""
import chess
import random
from typing import Optional, Tuple

class ChessEngine:
    """象棋引擎封装"""
    
    def __init__(self, difficulty: int = 1, stockfish_path: Optional[str] = None):
        """
        初始化引擎
        Args:
            difficulty: 难度等级 1-3 (1=简单, 2=中等, 3=困难)
            stockfish_path: Stockfish可执行文件路径 (可选)
        """
        self.difficulty = difficulty
        self.stockfish = None
        self.board = chess.Board()
        
        # 尝试加载 Stockfish
        if stockfish_path:
            try:
                import chess.engine as ce
                self.stockfish = ce.SimpleEngine.popen_uci(stockfish_path)
                print(f"✓ 已加载 Stockfish: {stockfish_path}")
            except Exception as e:
                print(f"✗ 无法加载 Stockfish: {e}")
                print("  将使用内置AI")
        else:
            # 自动检测 Stockfish
            try:
                import chess.engine as ce
                self.stockfish = ce.SimpleEngine.popen_uci("stockfish")
                print("✓ 已自动加载 Stockfish")
            except:
                print("未找到 Stockfish，将使用内置AI")
    
    def set_difficulty(self, difficulty: int):
        """设置难度 (1-3)"""
        self.difficulty = max(1, min(3, difficulty))
        print(f"难度设置为: {['', '简单', '中等', '困难'][self.difficulty]}")
    
    def get_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        获取最佳着法
        Args:
            board: 当前棋盘状态
        Returns:
            最佳着法
        """
        if self.stockfish:
            return self._get_stockfish_move(board)
        else:
            return self._get_builtin_move(board)
    
    def _get_stockfish_move(self, board: chess.Board) -> Optional[chess.Move]:
        """使用 Stockfish 获取着法"""
        # 根据难度设置搜索深度和时间
        depth_map = {1: 5, 2: 10, 3: 15}
        time_map = {1: 0.1, 2: 0.5, 3: 1.0}
        
        try:
            import chess.engine as ce
            result = self.stockfish.play(
                board, 
                limit=ce.Limit(
                    depth=depth_map[self.difficulty],
                    time=time_map[self.difficulty]
                )
            )
            return result.move
        except Exception as e:
            print(f"Stockfish 错误: {e}")
            return self._get_builtin_move(board)
    
    def _get_builtin_move(self, board: chess.Board) -> Optional[chess.Move]:
        """内置简单AI"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
        
        if self.difficulty == 1:
            # 简单：随机走法
            return random.choice(legal_moves)
        
        elif self.difficulty == 2:
            # 中等：优先吃子和将军
            return self._medium_ai(board, legal_moves)
        
        else:
            # 困难：使用极小化极大算法
            return self._hard_ai(board)
    
    def _medium_ai(self, board: chess.Board, legal_moves: list) -> chess.Move:
        """中等难度AI"""
        # 棋子价值
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0
        }
        
        best_move = None
        best_score = -9999
        
        for move in legal_moves:
            score = 0
            
            # 吃子得分
            if board.is_capture(move):
                captured = board.piece_at(move.to_square)
                if captured:
                    score += piece_values.get(captured.piece_type, 0)
            
            # 将军加分
            board.push(move)
            if board.is_check():
                score += 50
            board.pop()
            
            # 随机因素
            score += random.randint(0, 10)
            
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _hard_ai(self, board: chess.Board) -> chess.Move:
        """困难难度AI - 使用Minimax算法"""
        best_move = None
        best_score = -9999
        depth = 3  # 搜索深度
        
        for move in board.legal_moves:
            board.push(move)
            score = -self._minimax(board, depth - 1, -9999, 9999, False)
            board.pop()
            
            if score > best_score:
                best_score = score
                best_move = move
        
        return best_move
    
    def _minimax(self, board: chess.Board, depth: int, alpha: float, beta: float, 
                 maximizing: bool) -> float:
        """Minimax算法带Alpha-Beta剪枝"""
        if depth == 0 or board.is_game_over():
            return self._evaluate_board(board)
        
        if maximizing:
            max_eval = -9999
            for move in board.legal_moves:
                board.push(move)
                eval_score = self._minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = 9999
            for move in board.legal_moves:
                board.push(move)
                eval_score = self._minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval
    
    def _evaluate_board(self, board: chess.Board) -> float:
        """评估棋盘局势"""
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0
        }
        
        score = 0
        
        # 棋子价值
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value
        
        # 位置价值表
        position_bonus = self._get_position_bonus(board)
        score += position_bonus
        
        # 中国象棋没有王车易位，但国际象棋有
        # 如果游戏结束
        if board.is_checkmate():
            if board.turn == chess.WHITE:
                return -9999
            else:
                return 9999
        
        return score
    
    def _get_position_bonus(self, board: chess.Board) -> float:
        """获取位置加成"""
        # 简化版位置评估
        bonus = 0
        
        # 中心控制
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        for sq in center_squares:
            piece = board.piece_at(sq)
            if piece:
                if piece.color == chess.WHITE:
                    bonus += 10
                else:
                    bonus -= 10
        
        return bonus
    
    def evaluate_position(self, board: chess.Board) -> Tuple[float, float, float]:
        """
        评估当前局面，返回 (评估分数, 白方胜率, 黑方胜率)
        Args:
            board: 当前棋盘状态
        Returns:
            (eval_score, white_win_prob, black_win_prob)
        """
        if self.stockfish:
            try:
                import chess.engine as ce
                info = self.stockfish.analyse(board, ce.Limit(depth=15))
                score = info["score"].relative
                
                if score.is_mate():
                    mate_in = score.mate()
                    if mate_in > 0:
                        # 白方将杀
                        eval_cp = 10000 - mate_in * 100
                    else:
                        # 黑方将杀
                        eval_cp = -10000 - mate_in * 100
                else:
                    eval_cp = score.score()
                
            except Exception as e:
                print(f"Stockfish 评估错误: {e}")
                eval_cp = self._evaluate_board(board) * 10
        else:
            eval_cp = self._evaluate_board(board) * 10
        
        # 将评估分数转换为胜率（百分比，0-100）
        white_win_prob = self._eval_to_win_probability(eval_cp)
        # 黑方胜率应为 100 - 白方胜率，而不是 1 - white_win_prob
        black_win_prob = round(100.0 - white_win_prob, 1)
        
        return eval_cp, white_win_prob, black_win_prob
    
    def _eval_to_win_probability(self, eval_cp: float) -> float:
        """
        将评估分数（厘兵值）转换为胜率
        使用改进的公式
        """
        if eval_cp > 10000:
            return 99.9
        elif eval_cp < -10000:
            return 0.1
        
        # Logistic function
        # 参数调整以获得更合理的胜率曲线
        import math
        k = 0.004  # 控制曲线陡峭度
        win_prob = 1 / (1 + math.exp(-k * eval_cp))
        
        return round(win_prob * 100, 1)
    
    def get_move_analysis(self, board: chess.Board, move: chess.Move) -> dict:
        """
        分析某步棋的质量
        Args:
            board: 走棋前的局面
            move: 要分析的着法
        Returns:
            分析结果字典
        """
        # 走棋前的评估
        eval_before, white_prob_before, black_prob_before = self.evaluate_position(board)
        
        # 走棋后的评估
        board_copy = board.copy()
        board_copy.push(move)
        eval_after, white_prob_after, black_prob_after = self.evaluate_position(board_copy)
        
        # 计算评分变化
        eval_change = eval_after - eval_before
        prob_change = white_prob_after - white_prob_before
        
        # 判断棋步质量
        quality = self._classify_move(eval_change, board.turn)
        
        return {
            "move": move.uci(),
            "eval_before": eval_before,
            "eval_after": eval_after,
            "eval_change": eval_change,
            "white_win_prob_before": white_prob_before,
            "white_win_prob_after": white_prob_after,
            "black_win_prob_before": black_prob_before,
            "black_win_prob_after": black_prob_after,
            "prob_change": prob_change,
            "quality": quality,
            "is_check": board_copy.is_check(),
            "is_capture": board.is_capture(move),
            "is_checkmate": board_copy.is_checkmate()
        }
    
    def _classify_move(self, eval_change: float, color: bool) -> str:
        """分类棋步质量"""
        # 白方正数好，黑方负数好
        if color == chess.WHITE:
            change = eval_change
        else:
            change = -eval_change
        
        if change >= 100:
            return "极好棋"
        elif change >= 50:
            return "好棋"
        elif change >= 0:
            return "正常"
        elif change >= -50:
            return "缓棋"
        elif change >= -100:
            return "不精确"
        else:
            return "失误"


# 全局引擎实例
_engine_instance: Optional[ChessEngine] = None

def get_engine(difficulty: int = 1, stockfish_path: Optional[str] = None) -> ChessEngine:
    """获取全局引擎实例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ChessEngine(difficulty, stockfish_path)
    return _engine_instance