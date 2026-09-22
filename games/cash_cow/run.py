from games.cash_cow.game_config import GameConfig

def run_game_round():
    config = GameConfig()
    result = config.simulate_round()
    print("Resultado da rodada:", result)

if __name__ == "__main__":
    run_game_round()