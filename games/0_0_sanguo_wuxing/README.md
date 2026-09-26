# 《三国五行传》Stake Engine Math SDK M2d

本目录是 7×7 簇群玩法的权威数学原型，基于 Stake Engine Math SDK。M2d 在 M2c 完整玩法上增加了百万局精确快速回归和流式完整 Book 写出。

已实现：

- 7×7 盘面；
- H1–H5、L1–L5；
- W1 武魂 Wild、W2 天命 Wild；
- 四方向 5+ 簇群；
- 同一步 Wild 单一归属；
- 最高总赔付组合与确定性平局顺序；
- 同步消除、垂直掉落和补位；
- 50,000× 封顶；
- 双 Wild 正式免费旋转触发；
- 2×2 超大符号 ×2；
- 无赢局武魂救援；
- 将魂返场；
- 木、火、金、水、土五项功能；
- 功能数 ×2/×3/×5/×10 局末倍数；
- 初始 5 次免费旋转；
- 新 W2 收集和 1×1–7×7 武魂成长；
- 等级追加旋转与 ×5/×7/×10 武魂倍数；
- 自然免费模式专用 `FR0`；
- 100× Bonus Buy 专用 `FRB0`；
- M2c 事件合同、RTP 分项和分析工具。
- 多进程 eventless 精确状态机回归；
- 每局直接写入 worker zstd/LUT/sidecar 的流式 Book 输出。

## 环境

仓库基于 Stake Engine Math SDK 提交 `600a376`。需要 Python 3.12+。

```bash
make setup
```

## 生成 reel strips

```bash
env/bin/python games/0_0_sanguo_wuxing/generate_reels.py
env/bin/python games/0_0_sanguo_wuxing/generate_free_reels.py
```

基础 `BR0` 每条长 719；自然/购买免费 reel 每条长 7,190，以 0.1 个 W2/原始 reel 等效单位进行细粒度校准。

## 快速验证

```bash
env/bin/python games/0_0_sanguo_wuxing/smoke_test.py
env/bin/python -m pytest tests/test_sanguo_wuxing.py -q
```

## 生成 SDK 结果

```bash
env/bin/python games/0_0_sanguo_wuxing/run.py
```

结果会以 RGS 校验所需的压缩格式写入 `games/0_0_sanguo_wuxing/library/publish_files/`。默认同时生成 `base` 与 `bonus` 各 10,000 局。

默认运行 10,000 局。扩大样本可使用：

```bash
SANGUO_SIM_COUNT=100000 \
SANGUO_MODES=base,bonus \
SANGUO_THREADS=4 \
env/bin/python games/0_0_sanguo_wuxing/run.py
```

分析分项：

```bash
env/bin/python games/0_0_sanguo_wuxing/analyze_m2c.py \
  --label m2c_candidate_100k \
  --output games/0_0_sanguo_wuxing/validation/m2c_100k_summary.json
```

百万局快速回归：

```bash
PYTHONPATH=games/0_0_sanguo_wuxing \
env/bin/python games/0_0_sanguo_wuxing/fast_regression.py \
  --sims 1000000 \
  --workers 8 \
  --modes base,bonus \
  --output games/0_0_sanguo_wuxing/validation/m2d_fast_regression.json
```

当前 M2d 开发候选：

- 普通模式：94.7121%，95% 区间 86.1726%–103.2516%；
- 自然免费触发约 1/223，免费贡献 26.9248%；
- 100× Bonus Buy：95.4634%，95% 区间 93.6074%–97.3194%；
- 96%均位于两模式置信区间；
- 完整 Book 流式烟雾测试的 Books/LUT/sidecar 哈希通过；
- 下一数学门槛为每模式至少 10,000,000 局候选回归。
