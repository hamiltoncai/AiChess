/**
 * Chess Game Frontend
 * 处理棋盘渲染、游戏逻辑和API通信
 */

// 游戏状态
const GameState = {
    board: null,
    playerColor: 'white',
    difficulty: 2,
    selectedSquare: null,
    legalMoves: [],
    gameOver: false,
    isPlayerTurn: true,
    moveHistory: [],
    commentary: []
};

// API 基础URL - 自动检测
let API_BASE;
if (window.location.protocol === 'file:') {
    // 如果直接打开HTML文件，使用localhost
    API_BASE = 'http://localhost:5001';
} else if (window.location.port === '5001') {
    // 如果已经是5001端口
    API_BASE = window.location.origin;
} else {
    // 其他情况，假设服务器在5001端口
    API_BASE = window.location.origin.replace(/:\d+$/, '') + ':5001';
}

console.log('API Base URL:', API_BASE);

// 棋盘配置
const BOARD_SIZE = 480;
const SQUARE_SIZE = BOARD_SIZE / 8;

// 颜色配置
const COLORS = {
    lightSquare: '#f0d9b5',
    darkSquare: '#b58863',
    selectedSquare: '#829769',
    legalMove: 'rgba(0, 128, 0, 0.4)',
    check: 'rgba(255, 0, 0, 0.5)',
    lastMove: 'rgba(255, 255, 0, 0.5)'
};

// Unicode棋子符号
const PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
};

// Canvas 和 Context
let canvas, ctx;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('chessboard');
    ctx = canvas.getContext('2d');
    
    canvas.addEventListener('click', handleBoardClick);
    
    // 初始化游戏（等 chess.js 加载完成，避免 Chess 未定义）
    const waitChess = () => new Promise((resolve) => {
        if (window.Chess) return resolve(true);
        
        const timer = setInterval(() => {
            if (window.Chess) {
                clearInterval(timer);
                resolve(true);
            }
        }, 50);
        
        // 最多等待 5 秒
        setTimeout(() => {
            clearInterval(timer);
            resolve(!!window.Chess);
        }, 5000);
    });

    waitChess().then((ok) => {
        if (!ok) {
            showError('Chess.js 未加载成功，请刷新页面后重试。');
            return;
        }
        newGame();
    });
});

/**
 * 开始新游戏
 */
async function newGame() {
    const difficulty = parseInt(document.getElementById('difficulty').value);
    const playerColor = document.getElementById('playerColor').value;
    
    console.log('Starting new game...', { difficulty, playerColor });
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/api/new_game`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: 'default',
                difficulty: difficulty,
                player_color: playerColor
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('New game response:', data);
        
        if (data.success) {
            GameState.board = new Chess(data.fen);
            GameState.playerColor = playerColor;
            GameState.difficulty = difficulty;
            GameState.gameOver = false;
            GameState.isPlayerTurn = (playerColor === 'white');
            GameState.selectedSquare = null;
            GameState.legalMoves = [];
            GameState.moveHistory = [];
            GameState.commentary = [];
            
            // 清空历史显示
            document.getElementById('moveHistory').innerHTML = '<p style="color: #666; text-align: center;">暂无走法</p>';
            document.getElementById('commentaryPanel').innerHTML = '<p style="color: #666; text-align: center;">走一步棋开始评论</p>';
            
            // 重置评估
            updateEvaluation(0, 50, 50);
            
            // 渲染棋盘
            renderBoard();
            updateStatus();
            
            // 关闭游戏结束模态框
            document.getElementById('gameOverModal').classList.remove('show');
            
            // 如果玩家执黑，AI先走
            if (playerColor === 'black') {
                setTimeout(() => aiMove(), 500);
            }
        } else {
            showError('创建游戏失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('Failed to start new game:', error);
        showError('无法连接服务器，请确保后端已启动: python3 app.py\n错误: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * 渲染棋盘
 */
function renderBoard() {
    const board = GameState.board.board();
    const flipped = (GameState.playerColor === 'black');
    
    // 清空画布
    ctx.clearRect(0, 0, BOARD_SIZE, BOARD_SIZE);
    
    // 绘制棋盘格子
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            const displayRow = flipped ? 7 - row : row;
            const displayCol = flipped ? 7 - col : col;
            
            const isLight = (row + col) % 2 === 0;
            
            // 背景色
            ctx.fillStyle = isLight ? COLORS.lightSquare : COLORS.darkSquare;
            ctx.fillRect(displayCol * SQUARE_SIZE, displayRow * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE);
            
            // 高亮最后一步
            if (GameState.moveHistory.length > 0 && false) {
                // TODO: 高亮最后一步
            }
            
            // 高亮选中的格子
            if (GameState.selectedSquare) {
                const sq = GameState.selectedSquare;
                // chess.js board() 的行索引 row=0 对应 rank=8；所以这里用 rank=8-row
                const sqRank = parseInt(sq.charAt(1), 10);
                const sqRow = 8 - sqRank;
                const sqCol = sq.charCodeAt(0) - 'a'.charCodeAt(0);
                
                // renderBoard 内部已经根据 flipped 计算了 displayRow/displayCol，
                // 这里直接用 board 索引 row/col 去匹配即可。
                if (row === sqRow && col === sqCol) {
                    ctx.fillStyle = COLORS.selectedSquare;
                    ctx.fillRect(displayCol * SQUARE_SIZE, displayRow * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE);
                }
            }
            
            // 绘制合法走法提示
            if (GameState.legalMoves.length > 0) {
                const algCol = flipped ? 7 - col : col;
                const algRow = flipped ? 7 - row : row;
                const square = String.fromCharCode('a'.charCodeAt(0) + col) + String(8 - row);
                
                if (GameState.legalMoves.includes(square)) {
                    ctx.beginPath();
                    ctx.arc(displayCol * SQUARE_SIZE + SQUARE_SIZE / 2, 
                           displayRow * SQUARE_SIZE + SQUARE_SIZE / 2, 
                           SQUARE_SIZE / 6, 0, Math.PI * 2);
                    ctx.fillStyle = COLORS.legalMove;
                    ctx.fill();
                }
            }
            
            // 绘制棋子
            const piece = board[row][col];
            if (piece) {
                drawPiece(piece, displayCol, displayRow);
            }
        }
    }
    
    // 绘制坐标标签
    drawCoordinates(flipped);
}

/**
 * 绘制棋子
 */
function drawPiece(piece, col, row) {
    const symbol = PIECES[piece.type === 'p' ? piece.color === 'w' ? 'P' : 'p' :
                          piece.color === 'w' ? piece.type.toUpperCase() : piece.type.toLowerCase()];
    
    ctx.font = `${SQUARE_SIZE * 0.8}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // 阴影效果
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillText(symbol, col * SQUARE_SIZE + SQUARE_SIZE / 2 + 2, row * SQUARE_SIZE + SQUARE_SIZE / 2 + 2);
    
    // 棋子
    ctx.fillStyle = piece.color === 'w' ? '#ffffff' : '#000000';
    ctx.fillText(symbol, col * SQUARE_SIZE + SQUARE_SIZE / 2, row * SQUARE_SIZE + SQUARE_SIZE / 2);
}

/**
 * 绘制坐标标签
 */
function drawCoordinates(flipped) {
    ctx.font = '12px Arial';
    ctx.fillStyle = COLORS.darkSquare;
    
    const files = 'abcdefgh';
    
    for (let i = 0; i < 8; i++) {
        const file = flipped ? 7 - i : i;
        const rank = flipped ? i : 7 - i;
        
        // 文件 (a-h)
        ctx.textAlign = 'right';
        ctx.textBaseline = 'bottom';
        ctx.fillText(files[file], (i + 1) * SQUARE_SIZE - 2, BOARD_SIZE - 2);
        
        // 等级 (1-8)
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(String(rank + 1), i * SQUARE_SIZE + 2, 2);
    }
}

/**
 * 处理棋盘点击
 */
async function handleBoardClick(event) {
    if (GameState.gameOver || !GameState.isPlayerTurn) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const flipped = (GameState.playerColor === 'black');
    
    let col = Math.floor(x / SQUARE_SIZE);
    let row = Math.floor(y / SQUARE_SIZE);
    
    if (flipped) {
        col = 7 - col;
        row = 7 - row;
    }
    
    const square = String.fromCharCode('a'.charCodeAt(0) + col) + String(8 - row);
    
    // 获取当前方
    const turn = GameState.board.turn();
    const playerPiece = (GameState.playerColor === 'white') ? 'w' : 'b';
    
    // 如果已经选中了棋子
    if (GameState.selectedSquare) {
        // 点击同一个格子，取消选择
        if (GameState.selectedSquare === square) {
            GameState.selectedSquare = null;
            GameState.legalMoves = [];
            renderBoard();
            return;
        }
        
        // 尝试走棋
        const move = GameState.selectedSquare + square;
        
        // 检查是否是合法走法（包括升变）
        const moves = GameState.board.moves({ square: GameState.selectedSquare, verbose: true });
        const matchingMoves = moves.filter(m => m.to === square);
        
        if (matchingMoves.length > 0) {
            // 如果是兵升变，选择升变棋子
            if (matchingMoves.length > 1) {
                // 简化：默认升变为后
                await makeMove(GameState.selectedSquare + square + 'q');
            } else {
                await makeMove(move);
            }
            return;
        }
        
        // 点击其他格子，选择新棋子
        GameState.selectedSquare = null;
        GameState.legalMoves = [];
    }
    
    // 选择棋子
    const piece = GameState.board.get(square);
    if (piece && piece.color === playerPiece) {
        GameState.selectedSquare = square;
        GameState.legalMoves = GameState.board.moves({ square: square, verbose: true }).map(m => m.to);
        renderBoard();
    }
}

/**
 * 执行走棋
 */
async function makeMove(move) {
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE}/api/make_move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: 'default',
                move: move
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            GameState.board = new Chess(data.fen);
            GameState.selectedSquare = null;
            GameState.legalMoves = [];
            
            // 更新状态
            if (data.analysis) {
                updateEvaluation(
                    data.analysis.eval_after,
                    data.analysis.white_win_prob_after,
                    data.analysis.black_win_prob_after
                );
            }
            
            // 显示评论
            if (data.commentary) {
                addCommentary({
                    move: move,
                    analysis: data.analysis,
                    text: data.commentary
                });
            }
            
            // 更新走法历史
            updateMoveHistory(data.last_move, 'player');
            
            // 检查游戏结束
            if (data.is_checkmate) {
                GameState.gameOver = true;
                showGameOver('checkmate');
            } else if (data.is_game_over) {
                GameState.gameOver = true;
                showGameOver('draw');
            } else {
                // AI回合
                GameState.isPlayerTurn = false;
                updateStatus();
                renderBoard();
                
                // AI走棋
                setTimeout(() => aiMove(), 500);
            }
        } else {
            console.error('Move failed:', data.error);
        }
    } catch (error) {
        console.error('Failed to make move:', error);
    } finally {
        showLoading(false);
    }
}

/**
 * AI走棋
 */
async function aiMove() {
    if (GameState.gameOver) return;
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE}/api/ai_move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: 'default' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 更新棋盘
            GameState.board = new Chess(data.fen);
            
            // 更新评估
            if (data.analysis) {
                updateEvaluation(
                    data.analysis.eval_after,
                    data.analysis.white_win_prob_after,
                    data.analysis.black_win_prob_after
                );
            }
            
            // 显示评论
            if (data.commentary) {
                addCommentary({
                    move: data.move,
                    analysis: data.analysis,
                    text: data.commentary
                });
            }
            
            // 更新走法历史
            updateMoveHistory(data.move, 'ai');
            
            // 检查游戏结束
            if (data.is_checkmate) {
                GameState.gameOver = true;
                showGameOver('ai_win');
            } else if (data.is_game_over) {
                GameState.gameOver = true;
                showGameOver('draw');
            } else {
                GameState.isPlayerTurn = true;
            }
            
            renderBoard();
            updateStatus();
        } else {
            console.error('AI move failed:', data.error);
        }
    } catch (error) {
        console.error('Failed to get AI move:', error);
    } finally {
        showLoading(false);
    }
}

/**
 * 悔棋
 */
async function undoMove() {
    try {
        const response = await fetch(`${API_BASE}/api/undo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: 'default', moves: 2 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            GameState.board = new Chess(data.fen);
            GameState.gameOver = false;
            GameState.isPlayerTurn = (GameState.playerColor === 'white');
            GameState.selectedSquare = null;
            GameState.legalMoves = [];
            
            // 移除最后两条评论
            GameState.commentary = GameState.commentary.slice(0, -2);
            updateCommentaryPanel();
            
            renderBoard();
            updateStatus();
            
            // 重新评估
            await evaluatePosition();
        }
    } catch (error) {
        console.error('Failed to undo:', error);
    }
}

/**
 * 评估当前局面
 */
async function evaluatePosition() {
    try {
        const response = await fetch(`${API_BASE}/api/evaluate?game_id=default`);
        const data = await response.json();
        
        if (data.success) {
            updateEvaluation(data.eval_score, data.white_win_prob, data.black_win_prob);
        }
    } catch (error) {
        console.error('Failed to evaluate:', error);
    }
}

/**
 * 更新评估显示
 */
function updateEvaluation(evalScore, whiteProb, blackProb) {
    // 更新胜率条
    const evalFill = document.getElementById('evalFill');
    const percentage = whiteProb;
    const fillHeight = percentage;
    evalFill.style.height = fillHeight + '%';
    
    // 根据评估设置颜色
    if (whiteProb > 70) {
        evalFill.style.background = '#fff';
    } else if (whiteProb > 55) {
        evalFill.style.background = '#ccc';
    } else if (whiteProb < 30) {
        evalFill.style.background = '#333';
    } else {
        evalFill.style.background = '#888';
    }
    
    // 更新数值
    document.getElementById('whiteProb').textContent = whiteProb.toFixed(1) + '%';
    document.getElementById('blackProb').textContent = blackProb.toFixed(1) + '%';
    document.getElementById('evalScore').textContent = evalScore > 0 ? '+' + evalScore : evalScore;
}

/**
 * 更新状态显示
 */
function updateStatus() {
    const statusBar = document.getElementById('statusBar');
    const turn = GameState.board.turn() === 'w' ? '白方' : '黑方';
    const isPlayer = (GameState.board.turn() === 'w') === (GameState.playerColor === 'white');
    
    let status = isPlayer ? '轮到你走棋' : 'AI思考中...';
    
    if (GameState.board.in_check()) {
        status = `${turn} - 将军!`;
        statusBar.classList.add('check');
    } else {
        statusBar.classList.remove('check');
    }
    
    if (GameState.gameOver) {
        statusBar.classList.remove('check');
    }
    
    statusBar.textContent = status;
    
    // 更新回合指示
    const boardWrapper = document.getElementById('boardWrapper');
    boardWrapper.dataset.turn = GameState.board.turn() === 'w' ? '⚪ 白方回合' : '⚫ 黑方回合';
}

/**
 * 更新走法历史
 */
function updateMoveHistory(move, who) {
    GameState.moveHistory.push({ move, who });
    
    const history = GameState.board.history();
    const historyDiv = document.getElementById('moveHistory');
    let html = '';
    
    for (let i = 0; i < history.length; i += 2) {
        const moveNum = Math.floor(i / 2) + 1;
        const whiteMove = history[i] || '';
        const blackMove = history[i + 1] || '';
        
        html += `<div class="move-item">
            <span class="move-number">${moveNum}.</span>
            <span class="move-white">${whiteMove}</span>
            <span class="move-black">${blackMove}</span>
        </div>`;
    }
    
    historyDiv.innerHTML = html;
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

/**
 * 添加评论
 */
function addCommentary(item) {
    GameState.commentary.push(item);
    updateCommentaryPanel();
}

/**
 * 更新评论面板
 */
function updateCommentaryPanel() {
    const panel = document.getElementById('commentaryPanel');
    
    if (GameState.commentary.length === 0) {
        panel.innerHTML = '<p style="color: #666; text-align: center;">走一步棋开始评论</p>';
        return;
    }
    
    const history = GameState.board.history();
    let html = '';
    
    // 只显示最近5条评论
    const recent = GameState.commentary.slice(-5);
    
    recent.forEach((item, index) => {
        const moveNum = GameState.commentary.length - recent.length + index + 1;
        const san = history[moveNum - 1] || item.move;
        
        let qualityClass = 'quality-normal';
        let qualityText = '正常';
        
        if (item.analysis) {
            qualityText = item.analysis.quality || '正常';
            if (qualityText.includes('极好') || qualityText.includes('好')) {
                qualityClass = 'quality-excellent';
            } else if (qualityText.includes('缓')) {
                qualityClass = 'quality-inaccuracy';
            } else if (qualityText.includes('失误')) {
                qualityClass = 'quality-mistake';
            }
        }
        
        html += `<div class="commentary-item">
            <div class="commentary-move">
                ${moveNum}. ${san}
                <span class="commentary-quality ${qualityClass}">${qualityText}</span>
            </div>
            <div class="commentary-text">${item.text}</div>
        </div>`;
    });
    
    panel.innerHTML = html;
    panel.scrollTop = panel.scrollHeight;
}

/**
 * 显示游戏结束
 */
function showGameOver(reason) {
    const modal = document.getElementById('gameOverModal');
    const title = document.getElementById('gameOverTitle');
    const message = document.getElementById('gameOverMessage');
    
    if (reason === 'checkmate') {
        const winner = GameState.board.turn() === 'b' ? '白方' : '黑方';
        const isPlayerWin = (winner === '白方' && GameState.playerColor === 'white') ||
                            (winner === '黑方' && GameState.playerColor === 'black');
        
        title.textContent = isPlayerWin ? '🎉 恭喜获胜!' : '😢 AI获胜';
        message.textContent = `${winner}获得胜利！`;
    } else {
        title.textContent = '🤝 和棋';
        message.textContent = '游戏结束，双方握手言和。';
    }
    
    modal.classList.add('show');
}

/**
 * 显示/隐藏加载动画
 */
function showLoading(show) {
    document.getElementById('loading').classList.toggle('show', show);
}

/**
 * 显示错误消息
 */
function showError(message) {
    alert(message);
}

/**
 * 更新LLM配置面板
 */
function updateLLMConfig() {
    const backend = document.getElementById('llmBackend').value;
    const panel = document.getElementById('llmConfigPanel');
    
    if (backend === 'none') {
        panel.style.display = 'none';
        updateLLMStatus(false, '未启用');
        // 通知后端关闭评论（断开已连接的 Ollama/OpenCode）
        fetch(`${API_BASE}/api/configure_llm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: 'default', backend: 'none' })
        }).catch(() => {});
    } else {
        panel.style.display = 'block';
        
        if (backend === 'ollama') {
            document.getElementById('llmBaseUrl').value = 'http://localhost:11434';
            document.getElementById('llmModel').value = 'qwen3:0.6b';
        } else {
            document.getElementById('llmBaseUrl').value = 'http://localhost:3000';
            document.getElementById('llmModel').value = 'default';
        }
        
        updateLLMStatus(false, '点击连接');
    }
}

/**
 * 连接LLM
 */
async function connectLLM() {
    const backend = document.getElementById('llmBackend').value;
    const baseUrl = document.getElementById('llmBaseUrl').value || '';
    const model = document.getElementById('llmModel').value || '';
    
    console.log('Connecting to LLM...', { backend, baseUrl, model });
    updateLLMStatus(false, '连接中...');
    
    try {
        const response = await fetch(`${API_BASE}/api/configure_llm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: 'default',
                backend: backend,
                base_url: baseUrl || undefined,
                model: model || undefined
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('LLM connection response:', data);
        
        if (data.success && data.available) {
            updateLLMStatus(true, `✓ 已连接 (${backend})`);
        } else {
            updateLLMStatus(false, '✗ 连接失败');
            alert('LLM连接失败，请检查:\n1. ' + (backend === 'ollama' ? 'Ollama服务是否运行 (http://localhost:11434)' : 'OpenCode服务是否运行') + '\n2. 端口是否正确');
        }
    } catch (error) {
        updateLLMStatus(false, '✗ 连接错误');
        console.error('LLM connection failed:', error);
        alert('LLM连接错误: ' + error.message + '\n\n请确保后端服务已启动: python3 app.py');
    }
}

/**
 * 更新LLM状态显示
 */
function updateLLMStatus(active, text) {
    const status = document.getElementById('llmStatus');
    status.className = 'llm-status' + (active ? ' active' : '');
    status.querySelector('span').textContent = text;
}

// Expose functions for inline onclick handlers in index.html
window.newGame = newGame;
window.undoMove = undoMove;
window.connectLLM = connectLLM;
window.updateLLMConfig = updateLLMConfig;