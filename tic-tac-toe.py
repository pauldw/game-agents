'''
Tic Tac Toe With Agents

Player Agents:
- NoRulesAgent: Randomizes turn taking, position, and player without regard for the rules of the game. Great at parties.
- RandomAgent: Places randomly.
- OneStepAheadAgent: Checks if it can win or lose in one move, but otherwise places randomly.
- MinimaxAgent: Uses minimax to find the best move.

Supervisor Agents:
- RegularReferee: Checks if the moves are legal, and if the game is over.
- NoPenaltiesReferee: Only checks to see if the game is over. Allows all moves.

Note that code is not shared between agents to make the complexity of each agent clearer.

Usage:
python tic-tac-toe.py [debug]
'''
from enum import Enum
import random
import sys

# TODO These should be in separate enums that distinguish between the player and the board state. (But if Gato can get away with mixing modalities, so can I.)
X = 0
O = 1
EMPTY = 2
REFEREE = 3

# For player integer to string
playermap = {X: "X", O: "O", REFEREE: "R"}

def log(player: int, s: str) -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        print(f"{playermap[player]}: {s}", flush=True)

class Coordinate:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col

    def __str__(self):
        return f"({self.row}, {self.col})"
    
    def __repr__(self):
        return str(self)

class Board:
    def __init__(self):
        self.board = [[EMPTY for _ in range(3)] for _ in range(3)]

    def place(self, coordinate: Coordinate, player: int) -> None:
        self.board[coordinate.row][coordinate.col] = player

    def pretty_print(self) -> None:
        for row in self.board:
            for col in row:
                if col == X:
                    print("X", end="")
                elif col == O:
                    print("O", end="")
                else:
                    print("-", end="")
            print()

    def __hash__(self):
        return hash(tuple(tuple(row) for row in self.board))

    def iter(self):
        for row in self.board:
            for col in row:
                yield col
    
    def __getitem__(self, key):
        return self.board[key]
    
    def copy(self):
        new_board = Board()
        for row in range(3):
            for col in range(3):
                new_board.board[row][col] = self.board[row][col]
        return new_board

class Move:
    def __init__(self, coordinate: Coordinate, player: int):
        self.coordinate = coordinate
        self.player = player

    def __str__(self):
        return f"{self.coordinate} {self.player}"

class Agent:
    pass

class NoRulesAgent(Agent):
    def __init__(self, player: int):
        self.player = player
        pass

    def step(self, board: Board) -> Move:
        turn = random.choice([True, False])

        if not turn:
            log(self.player, "Not taking a turn.")
            return None

        row = random.choice([0, 1, 2])
        col = random.choice([0, 1, 2])
        player = random.choice([X, O])
        log(self.player, f"Placing at ({row}, {col}) as {playermap[player]}")

        return Move(Coordinate(row, col), player)

class RandomAgent(Agent):
    def __init__(self, player: int):
        self.player = player

    def step(self, board: Board) -> Move:
        hist = self.board_histogram(board)
        
        winner = self.check_win(board)
        
        if winner == self.player:
            log(self.player, "I won!")
            return None
        
        if winner != EMPTY:
            log(self.player, "I lost!")
            return None

        if hist[EMPTY] == 0:
            log(self.player, "Draw!")
            return None

        if (hist[O] >= hist[X]) and self.player == O:
            log(self.player, "Not my turn, X is next.")
            return None
        
        if (hist[X] > hist[O]) and self.player == X:
            log(self.player, "Not my turn, O is next.")
            return None
        
        random_free_spot = random.choice(self.free_spots(board))
        log(self.player, f"Placing at {random_free_spot}")

        return Move(random_free_spot, self.player)

    def board_histogram(self, board: Board) -> dict:
        hist = {X: 0, O: 0, EMPTY: 0}
        for pos in board.iter():
            hist[pos] += 1
        return hist

    def free_spots(self, board: Board) -> [Coordinate]:
        free = []
        for row in range(3):
            for col in range(3):
                if board[row][col] == EMPTY:
                    free.append(Coordinate(row, col))
        return free
    
    def check_win(self, board) -> int:
        # Check rows
        for row in range(3):
            if board[row][0] == board[row][1] == board[row][2]:
                return board[row][0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        
        if board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        
        return EMPTY
    
class OneStepAheadAgent(Agent):
    def __init__(self, player: int):
        self.player = player

    def step(self, board: Board) -> Move:
        hist = self.board_histogram(board)
        
        winner = self.check_win(board)
        
        if winner == self.player:
            log(self.player, "I won!")
            return None
        
        if winner != EMPTY:
            log(self.player, "I lost!")
            return None

        if hist[EMPTY] == 0:
            log(self.player, "Draw!")
            return None

        if (hist[O] >= hist[X]) and self.player == O:
            log(self.player, "Not my turn, X is next.")
            return None
        
        if (hist[X] > hist[O]) and self.player == X:
            log(self.player, "Not my turn, O is next.")
            return None

        # Imagine my own moves
        imagined_board = board.copy()
        for move in self.free_spots(board):
            imagined_board.place(move, self.player)
            if self.check_win(imagined_board) == self.player:
                log(self.player, f"I can win by placing at {move}, so I'm going to place there.")
                return Move(move, self.player)
            imagined_board.place(move, EMPTY)

        # Imagine the other player's move
        other_player = X if self.player == O else O
        imagined_board = board.copy()
        for move in self.free_spots(board):
            imagined_board.place(move, other_player)
            if self.check_win(imagined_board) == other_player:
                log(self.player, f"Other player can win by placing at {move}, so I'm going to place there.")
                return Move(move, self.player)
            imagined_board.place(move, EMPTY)

        # Otherwise, place randomly
        random_free_spot = random.choice(self.free_spots(board))
        log(self.player, f"Randomly placing at {random_free_spot}")

        return Move(random_free_spot, self.player)

    def board_histogram(self, board: Board) -> dict:
        hist = {X: 0, O: 0, EMPTY: 0}
        for pos in board.iter():
            hist[pos] += 1
        return hist

    def free_spots(self, board: Board) -> [Coordinate]:
        free = []
        for row in range(3):
            for col in range(3):
                if board[row][col] == EMPTY:
                    free.append(Coordinate(row, col))
        return free
    
    def check_win(self, board) -> int:
        # Check rows
        for row in range(3):
            if board[row][0] == board[row][1] == board[row][2]:
                return board[row][0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        
        if board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        
        return EMPTY

class MinimaxAgent(Agent):
    def __init__(self, player: int):
        self.player = player

    def step(self, board: Board) -> Move:
        hist = self.board_histogram(board)
        
        winner = self.check_win(board)
        
        if winner == self.player:
            log(self.player, "I won!")
            return None
        
        if winner != EMPTY:
            log(self.player, "I lost!")
            return None

        if hist[EMPTY] == 0:
            log(self.player, "Draw!")
            return None

        if (hist[O] >= hist[X]) and self.player == O:
            log(self.player, "Not my turn, X is next.")
            return None
        
        if (hist[X] > hist[O]) and self.player == X:
            log(self.player, "Not my turn, O is next.")
            return None

        # Place at a random highest value position
        position_values = self.position_values(board, self.player)
        highest_value = max(position_values.values())
        highest_value_positions = list({k: v for k, v in position_values.items() if v == highest_value}.keys())
        random_highest_value_position = random.choice(highest_value_positions)
        log(self.player, f"I'm going to place at a random highest value position: {random_highest_value_position}")
        return Move(random_highest_value_position, self.player)
    
    def position_values(self, board:Board, imagined_player: int) -> dict:
        # Note this doesn't memoize or deduplicate, so it's very slow
        values = {}
        imagined_board = board.copy()
        for move in self.free_spots(board):
            imagined_board.place(move, imagined_player)
            if self.check_win(imagined_board) == imagined_player:
                # We would win
                values[move] = 1
                continue
            if len(self.free_spots(imagined_board)) == 0:
                # We would draw
                values[move] = 0
                continue
            # Opponent would get to move, and could choose the best position for them
            values[move] = max(self.position_values(imagined_board, X if imagined_player == O else O).values()) * -1 # Their win is our loss
            imagined_board.place(move, EMPTY)

        return values

    def other_player(self) -> int:
        return X if self.player == O else O

    def board_histogram(self, board: Board) -> dict:
        hist = {X: 0, O: 0, EMPTY: 0}
        for pos in board.iter():
            hist[pos] += 1
        return hist

    def free_spots(self, board: Board) -> [Coordinate]:
        free = []
        for row in range(3):
            for col in range(3):
                if board[row][col] == EMPTY:
                    free.append(Coordinate(row, col))
        return free
    
    def check_win(self, board) -> int:
        # Check rows
        for row in range(3):
            if board[row][0] == board[row][1] == board[row][2]:
                return board[row][0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        
        if board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        
        return EMPTY

class Judgement(Enum):
    X_WINS = 0
    O_WINS = 1
    DRAW = 2
    X_PENALTY = 3
    O_PENALTY = 4

class RegularReferee:
    def __init__(self):
        pass

    def step(self, board: Board, x_move: Move, o_move: Move) -> Judgement:
        if x_move is not None and x_move.player != X:
            log(REFEREE, "X didn't put down the correct symbol. Penalty X.")
            return Judgement.X_PENALTY
        
        if o_move is not None and o_move.player != O:
            log(REFEREE, "O didn't put down the correct symbol. Penalty O.")
            return Judgement.O_PENALTY

        if x_move is not None and board[x_move.coordinate.row][x_move.coordinate.col] != EMPTY:
            log(REFEREE, "X moved on top of another piece. Penalty X.")
            return Judgement.X_PENALTY

        if o_move is not None and board[o_move.coordinate.row][o_move.coordinate.col] != EMPTY:
            log(REFEREE, "O moved on top of another piece. Penalty O.")
            return Judgement.O_PENALTY

        if x_move is not None and self.whose_turn(board) == O:
            log(REFEREE, "Not X's turn. Penalty X.")
            return Judgement.X_PENALTY

        if o_move is not None and self.whose_turn(board) == X:
            log(REFEREE, "Not O's turn. Penalty O.")
            return Judgement.O_PENALTY
        
        if self.check_win(board) == X:
            log(REFEREE, "X wins!")
            return Judgement.X_WINS

        if self.check_win(board) == O:
            log(REFEREE, "O wins!")
            return Judgement.O_WINS

        if all(pos is not EMPTY for pos in board.iter()) and self.check_win(board) == EMPTY:
            log(REFEREE, "Draw!")
            return Judgement.DRAW
        
        if x_move is None and self.whose_turn(board) == X:
            log(REFEREE, "X's turn but didn't go. Penalty X.")
            return Judgement.X_PENALTY

        if o_move is None and self.whose_turn(board) == O:
            log(REFEREE, "O's turn but didn't go. Penalty O.")
            return Judgement.O_PENALTY

    def whose_turn(self, board: Board) -> int:
        hist = self.board_histogram(board)
        if hist[O] >= hist[X]:
            return X
        return O
    
    def board_histogram(self, board: Board) -> dict:
        hist = {X: 0, O: 0, EMPTY: 0}
        for pos in board.iter():
            hist[pos] += 1
        return hist

    def check_win(self, board: Board) -> int:
        # Check rows
        for row in range(3):
            if board[row][0] == board[row][1] == board[row][2]:
                return board[row][0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        
        if board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        
        return EMPTY
    
class NoPenaltiesReferee:
    def __init__(self):
        pass

    def step(self, board: Board, x_move: Move, o_move: Move) -> Judgement:
        if self.check_win(board) == X:
            log(REFEREE, "X wins!")
            return Judgement.X_WINS

        if self.check_win(board) == O:
            log(REFEREE, "O wins!")
            return Judgement.O_WINS

        if all(pos is not EMPTY for pos in board.iter()) and self.check_win(board) == EMPTY:
            log(REFEREE, "Draw!")
            return Judgement.DRAW

    def check_win(self, board: Board) -> int:
        # Check rows
        for row in range(3):
            if board[row][0] == board[row][1] == board[row][2]:
                return board[row][0]
        
        # Check columns
        for col in range(3):
            if board[0][col] == board[1][col] == board[2][col]:
                return board[0][col]
        
        # Check diagonals
        if board[0][0] == board[1][1] == board[2][2]:
            return board[0][0]
        
        if board[0][2] == board[1][1] == board[2][0]:
            return board[0][2]
        
        return EMPTY
    
class Simulator:
    def __init__(self, agent_x: Agent, agent_o: Agent, agent_referee):
        self.players = [agent_x, agent_o]
        self.referee = agent_referee
        self.board = Board()

    def step(self) -> Judgement:
        moves = [agent.step(self.board) for agent in self.players]
        
        judgement = self.referee.step(self.board, moves[X], moves[O])
        if judgement is not None:
            return judgement
        
        for move in moves:
            if move is not None:
                self.board.place(move.coordinate, move.player)

        return None
        
    def run(self) -> Judgement:
        while True:
            if len(sys.argv) > 1 and sys.argv[1] == "debug":
                print()
                self.board.pretty_print()
                print()
            judgement = self.step()
            if judgement is not None:
                print()
                self.board.pretty_print()
                print()
                return judgement

def main():
    judgement_counts = {}
    
    for _ in range(0, 10):    
        agent_x = OneStepAheadAgent(X)
        agent_o = RandomAgent(O)
        agent_referee = RegularReferee()
        sim = Simulator(agent_x, agent_o, agent_referee)
        judgement = sim.run()
        judgement_counts[judgement] = judgement_counts.get(judgement, 0) + 1

    for key in sorted(judgement_counts.keys(), key=lambda x: x.value):
        print(f"{key}: {judgement_counts[key]}")

if __name__ == "__main__":
    main()
