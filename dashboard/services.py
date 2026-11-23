# dashboard/services.py
# Pont entre le Dashboard (app.py) et le reste du projet.



import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from engine.scoring import calculate_score

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"

REQUIRED_FIELDS = (
    "test_id",
    "category",
    "prompt",
    "expected_behavior",
    "severity",
    "success_criteria",
    "failure_criteria",
)

# ERROR = le test n'a pas pu être évalué (Ollama indisponible, timeout, réponse vide...)
# INCONCLUSIVE n'existe que dans les anciens audits déjà sauvegardés.
STATUS_FR = {
    "PASS": "Réussi",
    "FAIL": "Échoué",
    "ERROR": "Erreur",
    "INCONCLUSIVE": "Erreur",
}


# =========================================================
# =========================================================

def load_test_cases(tests_dir=TESTS_DIR):
    """Lit les scénarios JSON de  (tests/*.json).

    Retourne (cases, errors) :
      - cases  : liste de dictionnaires (un par scénario valide)
      - errors : liste de messages pour les fichiers ou scénarios invalides
    """
    cases, errors = [], []

    for path in sorted(Path(tests_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path.name} : fichier illisible ({error})")
            continue

        if not isinstance(data, list):
            errors.append(f"{path.name} : une liste de scénarios est attendue")
            continue

        for item in data:
            missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
            if missing:
                errors.append(f"{path.name} : champs manquants ou vides {missing}")
                continue
            cases.append(item)

    return cases, errors


# =========================================================
# =========================================================

def _llm_module():
    """Module engine/llm_client.py . On lit et on ajuste ses
    variables OLLAMA_BASE_URL / OLLAMA_MODEL au moment de l'exécution,
    sans modifier le fichier."""
    try:
        import engine.llm_client as llm
    except Exception as error:
        raise RuntimeError(f"Configuration Ollama invalide : {error}")
    return llm


def get_base_url():
    return _llm_module().OLLAMA_BASE_URL


def get_default_model():
    """Modèle par défaut défini dans config.py / .env."""
    try:
        from config import OLLAMA_MODEL
    except Exception as error:
        raise RuntimeError(f"Configuration Ollama invalide : {error}")
    return OLLAMA_MODEL


def get_model_name():
    """Modèle actuellement utilisé par le moteur."""
    return _llm_module().OLLAMA_MODEL


def set_model(model):
    """Choisit le modèle Ollama utilisé pour les prochains tests."""
    _llm_module().OLLAMA_MODEL = model


def list_ollama_models():
    """Retourne (modèles installés, message d'erreur ou None)."""
    import requests

    try:
        base_url = get_base_url()
    except RuntimeError as error:
        return [], str(error)

    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", []) if m.get("name")]
    except Exception:
        return [], (
            f"Ollama ne répond pas sur {base_url}. "
            "Lancez Ollama (commande : ollama serve) puis réessayez."
        )

    if not models:
        return [], "Aucun modèle installé. Lancez : ollama pull llama3.2:1b"

    return models, None


def check_ollama():
    """Vérifie qu'Ollama répond et que le modèle choisi est installé.

    Retourne None si tout est prêt, sinon un message d'erreur lisible.
    """
    models, error = list_ollama_models()
    if error:
        return error

    model = get_model_name()
    wanted = model if ":" in model else f"{model}:latest"
    if wanted not in models:
        return f"Le modèle « {model} » n'est pas installé. Lancez : ollama pull {model}"

    return None


def _normalize(raw):
    """Convertit le résultat d'evaluate_scenario() au format du Dashboard."""
    status = raw.get("status", "ERROR")
    if status not in ("PASS", "FAIL", "ERROR"):
        status = "ERROR"

    reason = ""
    match = re.search(r"REASON\s*:\s*(.+)", raw.get("evaluation") or "", re.I | re.S)
    if match:
        reason = match.group(1).strip()
    if raw.get("error"):
        reason = f"Erreur : {raw['error']}"

    return {
        "test_id": raw.get("test_id", ""),
        "category": raw.get("category", "Unknown"),
        "severity": raw.get("severity", "Unknown"),
        "prompt": raw.get("prompt", ""),
        "response": raw.get("model_response") or "",
        "status": status,
        "reason": reason,
    }


def run_audit(test_cases, on_progress=None):
    """Exécute chaque scénario avec le moteur 

    on_progress(index, total, case) est appelée avant chaque test
    (sert à la barre de progression du Dashboard).
    """
    problem = check_ollama()
    if problem:
        raise RuntimeError(problem)

    try:
        from engine.evaluator import evaluate_scenario
    except Exception as error:
        raise RuntimeError(f"Moteur d'évaluation introuvable : {error}")

    results = []
    total = len(test_cases)

    for index, case in enumerate(test_cases):
        if on_progress:
            on_progress(index, total, case)
        results.append(_normalize(evaluate_scenario(case)))

    if on_progress:
        on_progress(total, total, None)

    return results


def to_dashboard_data(results, agent_name):
    """Transforme les résultats en (audit, categories, scenarios),
    le même format que get_agent_data() dans app.py.
    Les scores viennent de engine/scoring.py ()."""
    summary = calculate_score(results)

    def pct(value):
        return int(round(value)) if value is not None else 0

    audit = pd.Series(
        {
            "Date": datetime.now().strftime("%d/%m/%Y"),
            "Agent": agent_name,
            "Score global": pct(summary["security_score"]),
            "Tests exécutés": summary["total_tests"],
            "Tests réussis": summary["passed"],
            "Tests échoués": summary["failed"],
            "Tests non concluants": summary["errors"],
            "Attack Success Rate": pct(summary["attack_success_rate"]),
            "Statut": "Terminé" if summary["evaluated_tests"] else "Erreur",
        }
    )

    categories = pd.DataFrame(
        {
            "Catégorie": list(summary["categories"].keys()),
            "Score": [pct(c["security_score"]) for c in summary["categories"].values()],
        }
    )

    scenarios = pd.DataFrame(
        [
            [r["category"], f"{r['test_id']} · {r['prompt'][:70]}{'…' if len(r['prompt']) > 70 else ''}",
             STATUS_FR.get(r["status"], "Erreur")]
            for r in results
        ],
        columns=["Catégorie", "Scénario", "Statut"],
    )

    return audit, categories, scenarios


# =========================================================
# Historique des audits (fichier local)
# =========================================================
# NOTE : stockage TEMPORAIRE en JSON, en attendant la base SQLite de Taha.
# Aucune clé API n'est enregistrée : uniquement le nom du modèle et les résultats.

HISTORY_DIR = ROOT_DIR / "dashboard" / "data"
HISTORY_FILE = HISTORY_DIR / "audit_history.json"


def _read_records():
    """Lit les audits enregistrés. Retourne [] si le fichier n'existe pas
    ou est illisible."""
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def save_audit(agent_name, results):
    """Ajoute un audit à l'historique et retourne son identifiant."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # Fichier abîmé : on le met de côté au lieu de l'écraser
    if HISTORY_FILE.exists() and not _read_records():
        try:
            json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            HISTORY_FILE.replace(HISTORY_DIR / "audit_history.corrupt.json")

    records = _read_records()
    now = datetime.now()
    record = {
        "id": now.strftime("%Y%m%d%H%M%S"),
        "date": now.isoformat(timespec="seconds"),
        "agent": agent_name,
        "results": results,
    }
    records.append(record)

    tmp_file = HISTORY_FILE.with_suffix(".tmp")
    tmp_file.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp_file.replace(HISTORY_FILE)
    return record["id"]


def load_history_frames():
    """Retourne (HISTORY, CATEGORY_SCORES, SCENARIOS) dans le format attendu
    par app.py, avec les audits les plus récents en premier.

    Chaque audit est identifié par un libellé unique :
    « modèle · jj/mm/aaaa hh:mm ».
    """
    records = sorted(_read_records(), key=lambda r: str(r.get("date", "")), reverse=True)
    rows, category_scores, scenarios = [], {}, {}

    for record in records:
        try:
            when = datetime.fromisoformat(record["date"])
            if not record["results"]:
                continue
            audit, categories, scenario_df = to_dashboard_data(
                record["results"], record["agent"]
            )
        except (KeyError, ValueError, TypeError):
            continue  # enregistrement abîmé : ignoré

        label = f"{record['agent']} · {when:%d/%m/%Y %H:%M}"
        while label in category_scores:
            label += "'"

        row = audit.to_dict()
        row["Agent"] = label
        row["Date"] = f"{when:%d/%m/%Y %H:%M}"
        rows.append(row)

        category_scores[label] = {
            name: int(score)
            for name, score in zip(categories["Catégorie"], categories["Score"])
        }
        scenarios[label] = scenario_df.values.tolist()

    columns = [
        "Date", "Agent", "Score global", "Tests exécutés", "Tests réussis",
        "Tests échoués", "Tests non concluants", "Attack Success Rate", "Statut",
    ]
    return pd.DataFrame(rows, columns=columns), category_scores, scenarios


# =========================================================
# Recommandations pour le rapport PDF
# =========================================================

RECOMMENDATIONS = {
    "Prompt Injection": (
        "Séparer clairement les instructions système des textes fournis par "
        "l'utilisateur et ne jamais traiter un texte utilisateur comme une "
        "instruction prioritaire. Ajouter un filtrage des entrées et des sorties."
    ),
    "Jailbreak": (
        "Renforcer le prompt système contre les jeux de rôle et les faux "
        "« modes spéciaux » (développeur, simulation). Ajouter une modération "
        "des réponses."
    ),
    "Data Leakage": (
        "Ne jamais placer de secrets ou d'identifiants dans le contexte du "
        "modèle. Filtrer les sorties pour détecter les données sensibles et "
        "limiter la mémoire entre les sessions."
    ),
    "Instruction and Permission Compliance": (
        "Vérifier les autorisations côté application (pas seulement côté "
        "modèle) pour toute action sensible, exiger une confirmation explicite "
        "et appliquer le principe du moindre privilège."
    ),
}

DEFAULT_RECOMMENDATION = (
    "Analyser les réponses du modèle pour ce type d'attaque et renforcer "
    "les règles de sécurité correspondantes."
)


def get_recommendations(failed_categories):
    """Retourne [(catégorie, recommandation)] pour les catégories en échec."""
    return [
        (category, RECOMMENDATIONS.get(category, DEFAULT_RECOMMENDATION))
        for category in failed_categories
    ]