"""Build phase2/report figures and tables for repo–PR concentration."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MASTER = ROOT / "phase2" / "data" / "curated" / "prs_master.csv"
AIDEV_REPO = ROOT.parent / "AIDev" / "repository.parquet"

# Monorepos / toolchains that are hard to build or benchmark locally.
HEAVY_REPOS = {
    "mochilang/mochi",
    "github/gh-aw",
    "github/gh-aw-mcpg",
    "dotnet/runtime",
    "dotnet/aspnetcore",
    "dotnet/sdk",
    "dotnet/razor",
    "dotnet/dotnet",
    "openclaw/openclaw",
    "OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager",
    "MontrealAI/AGI-Alpha-Agent-v0",
    "web-infra-dev/rspack",
    "Z3Prover/z3",
    "PrefectHQ/prefect",
    "oxc-project/oxc",
    "fastrepl/char",
    "devantler-tech/ksail",
    "aptos-labs/aptos-core",
    "OpenRakis/Spice86",
    "jstime/jstime",
    "pytorch/pytorch",
    "pytorch/ao",
    "Azure/azure-sdk-for-net",
    "Azure/azure-sdk-for-java",
    "Azure/azure-sdk-for-rust",
    "Azure/azure-dev",
    "Azure/azure-service-operator",
    "Azure/azure-cosmos-dotnet-v3",
    "microsoft/onnxruntime",
    "microsoft/typescript-go",
    "microsoft/typespec",
    "microsoft/openvmm",
    "microsoft/CCF",
    "microsoft/DiskANN",
    "microsoft/FluidFramework",
    "vllm-project/vllm",
    "NVIDIA/TensorRT-LLM",
    "NVIDIA/Fuser",
    "StarRocks/starrocks",
    "cockroachdb/cockroach",
    "pingcap/tidb",
    "neondatabase/neon",
    "risingwavelabs/risingwave",
    "tenstorrent/tt-metal",
    "ROCm/TheRock",
    "ROCm/iris",
    "ROCm/rocm-libraries",
    "vercel/next.js",
    "ray-project/ray",
    "langgenius/dify",
    "OpenMS/OpenMS",
    "ydb-platform/ydb",
    "near/nearcore",
    "NethermindEth/nethermind",
    "celestiaorg/celestia-core",
    "celestiaorg/celestia-app",
    "valkey-io/valkey-glide",
    "BoundaryML/baml",
    "spellshift/realm",
    "getsentry/sentry",
    "datahub-project/datahub",
    "open-metadata/OpenMetadata",
    "huggingface/tokenizers",
    "sgl-project/sglang",
    "kvcache-ai/Mooncake",
    "marin-community/levanter",
    "marin-community/marin",
    "flagos-ai/FlagGems",
    "deepseek-ai/DeepSeek-V3",
    "roboflow/rf-detr",
    "roboflow/inference",
    "ml-explore/mlx-lm",
    "facioquo/stock-indicators-python",  # needs .NET / pythonnet
    "Chia-Network/chia-blockchain",
    "grafana/grafana",
    "RocketChat/Rocket.Chat",
    "mui/mui-x",
    "TanStack/router",
    "fern-api/fern",
    "kubb-labs/kubb",
    "SkBlaz/py3plex",
    "1c-syntax/bsl-language-server",
    "open-telemetry/opentelemetry-java-instrumentation",
    "asynkron/protoactor-dotnet",
    "MudBlazor/MudBlazor",
    "gui-cs/Terminal.Gui",
    "elsa-workflows/elsa-core",
    "OrchardCMS/OrchardCore",
    "Puchaczov/Musoq",
    "litedb-org/LiteDB",
    "OpenHFT/Chronicle-Wire",
    "OpenHFT/Chronicle-Threads",
    "OpenHFT/Chronicle-Logger",
    "frostwire/frostwire",
    "projectcalico/calico",
    "netdata/netdata",
    "mattermost/mattermost-plugin-agents",
    "sqlfluff/sqlfluff",
    "quarylabs/sqruff",
    "gridaco/grida",
    "voidzero-dev/vite-plus",
    "jlucaso1/whatsapp-rust",
    "mediar-ai/terminator",
    "zeroclaw-labs/zeroclaw",
    "SOVEREIGN-NET/The-Sovereign-Network",
    "nearai/ironclaw",
    "vinhnx/VTCode",
    "rudrankriyam/App-Store-Connect-CLI",
}

LIGHT_EXCLUDE_KEYWORDS = (
    "cuda",
    "rocm",
    "tensor",
    "torch",
    "metal",
    "android",
    "gpu",
    "triton",
    "llvm",
    "wasm",
    "dotnet",
    "aspnet",
)


def primary_ext(files: object) -> str:
    text = str(files or "")
    exts: set[str] = set()
    for part in text.split("|"):
        suffix = Path(part.strip()).suffix.lower()
        if suffix:
            exts.add(suffix)
    order = [
        ".py",
        ".go",
        ".rs",
        ".cs",
        ".kt",
        ".java",
        ".cpp",
        ".cc",
        ".ts",
        ".js",
        ".tsx",
        ".c",
        ".h",
    ]
    for item in order:
        if item in exts:
            return item
    return sorted(exts)[0] if exts else "unknown"


def classify_row(row: pd.Series) -> str:
    repo = row["repo"]
    if repo in HEAVY_REPOS:
        return "heavy"
    name = repo.lower()
    if any(k in name for k in LIGHT_EXCLUDE_KEYWORDS):
        return "mid"
    # Walk-volume compile candidates: small Python packages.
    if row["primary_perf_ext"] == ".py" and row["n_prs"] <= 10:
        stars = row.get("stars")
        if pd.isna(stars) or stars < 15000:
            return "light_py"
    if row["primary_perf_ext"] == ".go" and row["n_prs"] <= 12:
        return "light_go"
    return "mid"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(MASTER)
    m["lang_ext"] = m["perf_files"].map(primary_ext)

    repo_n = m.groupby("repo").size().rename("n_prs")
    repo_lang = (
        m.groupby("repo")["lang_ext"]
        .agg(lambda s: s.value_counts().index[0])
        .rename("primary_perf_ext")
    )
    repo_agents = m.groupby("repo")["agent"].nunique().rename("n_agents")
    repo_al = m.groupby("repo")["has_agentlogs"].sum().rename("n_with_agentlogs")
    repo_out = m.groupby(["repo", "outcome"]).size().unstack(fill_value=0)

    df = pd.concat([repo_n, repo_lang, repo_agents, repo_al], axis=1)
    for col in ("merged", "closed_unmerged", "open"):
        df[col] = repo_out[col] if col in repo_out.columns else 0
    df = df.reset_index()

    if AIDEV_REPO.exists():
        meta = pd.read_parquet(AIDEV_REPO)[["full_name", "language", "stars", "forks"]]
        df = df.merge(meta, left_on="repo", right_on="full_name", how="left")
        df = df.drop(columns=["full_name"])
    else:
        df["language"] = pd.NA
        df["stars"] = pd.NA
        df["forks"] = pd.NA

    df["tier"] = df.apply(classify_row, axis=1)
    df = df.sort_values("n_prs", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    total = int(df["n_prs"].sum())
    df["share"] = df["n_prs"] / total
    df["cum_prs"] = df["n_prs"].cumsum()
    df["cum_share"] = df["cum_prs"] / total
    df.to_csv(OUT / "repo_pr_distribution.csv", index=False)

    # Language summary at PR level
    lang_pr = m["lang_ext"].value_counts().rename_axis("ext").reset_index(name="n_prs")
    lang_pr["share"] = lang_pr["n_prs"] / len(m)
    lang_pr.to_csv(OUT / "perf_file_language_by_pr.csv", index=False)

    tier_repo = df.groupby("tier").size().rename("n_repos")
    tier_pr = df.groupby("tier")["n_prs"].sum().rename("n_prs")
    tier = pd.concat([tier_repo, tier_pr], axis=1).reset_index()
    tier["pr_share"] = tier["n_prs"] / total
    tier.to_csv(OUT / "build_tier_summary.csv", index=False)

    light = df[df["tier"].isin(["light_py", "light_go"])].copy()
    light.to_csv(OUT / "light_repo_candidates.csv", index=False)

    # ---- figures ----
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 160,
            "font.size": 9,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
        }
    )

    # Figure 1: top 40 repos
    top = df.head(40).iloc[::-1]
    colors = []
    for tier_name in top["tier"]:
        colors.append(
            {
                "heavy": "#C44E52",
                "mid": "#4C78A8",
                "light_py": "#55A868",
                "light_go": "#8AD0A5",
            }.get(tier_name, "#4C78A8")
        )
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.barh(top["repo"], top["n_prs"], color=colors)
    ax.set_xlabel("Number of performance PRs")
    ax.set_ylabel("Repository")
    ax.set_title("Top 40 repositories by performance-PR count (n=4,146)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_repo_pr_top40.png")
    plt.close(fig)

    # Figure 2: all 289 repos, sorted descending (dense bars)
    fig, ax = plt.subplots(figsize=(16, 5))
    x = range(len(df))
    bar_colors = [
        {
            "heavy": "#C44E52",
            "mid": "#4C78A8",
            "light_py": "#55A868",
            "light_go": "#8AD0A5",
        }.get(t, "#4C78A8")
        for t in df["tier"]
    ]
    ax.bar(x, df["n_prs"], color=bar_colors, width=1.0)
    ax.set_xlabel("Repositories (sorted by PR count, descending)")
    ax.set_ylabel("Number of performance PRs")
    ax.set_title("All 289 repositories: performance-PR distribution")
    ax.set_xlim(-1, len(df))
    # label only top 8 tick positions
    ticks = list(range(0, min(8, len(df))))
    ax.set_xticks(ticks)
    ax.set_xticklabels([df.loc[i, "repo"].split("/")[-1] for i in ticks], rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_repo_pr_all289.png")
    plt.close(fig)

    # Figure 3: cumulative share
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["rank"], df["cum_share"] * 100, color="#4C78A8", lw=2)
    ax.axhline(50, color="#999", ls="--", lw=1)
    ax.axhline(80, color="#999", ls="--", lw=1)
    ax.set_xlabel("Repository rank (by PR count)")
    ax.set_ylabel("Cumulative share of PRs (%)")
    ax.set_title("Concentration of 4,146 PRs across repositories")
    n50 = int((df["cum_share"] <= 0.5).sum() + 1)
    n80 = int((df["cum_share"] <= 0.8).sum() + 1)
    ax.annotate(f"50% ≈ top {n50} repos", xy=(n50, 50), xytext=(n50 + 20, 42))
    ax.annotate(f"80% ≈ top {n80} repos", xy=(n80, 80), xytext=(n80 + 15, 72))
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_repo_pr_cumulative.png")
    plt.close(fig)

    # Figure 4: language bars
    lang = lang_pr.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(lang["ext"], lang["n_prs"], color="#4C78A8")
    ax.set_xlabel("Number of PRs (by primary perf_files extension)")
    ax.set_title("Language proxy from performance-test file extensions")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_lang_ext_by_pr.png")
    plt.close(fig)

    # short markdown stats for README assembly
    meteo = df[df["repo"] == "meteostat/meteostat"]
    summary = {
        "n_prs": total,
        "n_repos": int(len(df)),
        "top10_share": float(df.head(10)["n_prs"].sum() / total),
        "top3_share": float(df.head(3)["n_prs"].sum() / total),
        "n50": n50,
        "n80": n80,
        "tier": tier.to_dict(orient="records"),
        "meteostat_prs": int(meteo["n_prs"].iloc[0]) if len(meteo) else 0,
        "light_py_repos": int((df["tier"] == "light_py").sum()),
        "light_py_prs": int(df.loc[df["tier"] == "light_py", "n_prs"].sum()),
        "light_go_repos": int((df["tier"] == "light_go").sum()),
        "light_go_prs": int(df.loc[df["tier"] == "light_go", "n_prs"].sum()),
        "heavy_repos": int((df["tier"] == "heavy").sum()),
        "heavy_prs": int(df.loc[df["tier"] == "heavy", "n_prs"].sum()),
    }
    pd.Series(summary).to_json(OUT / "summary_stats.json")
    print("wrote report artifacts to", OUT)
    print(summary)


if __name__ == "__main__":
    main()
