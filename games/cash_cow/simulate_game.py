from games.cash_cow.game_config import GameConfig

def simulate_game_rounds(rounds=100_000):
    config = GameConfig()
    total_payout = 0

    for _ in range(rounds):
        result = config.simulate_round()
        total_payout += result["payout"]

    rtp = (total_payout / rounds) * 100
    print(f"Simulated {rounds} rounds. Estimated RTP: {rtp:.2f}%")

if __name__ == "__main__":
    simulate_game_rounds()