"""
LLM Client
Pluggable LLM client. Disabled by default: returns deterministic stub
responses so the rest of the system never requires an API key.
"""

from typing import Any, Dict, Optional
import hashlib
import logging
import os

logger = logging.getLogger(__name__)


class LLMClient:
    """Pluggable LLM client driven by the ``llm`` configuration block."""

    def __init__(self, llm_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the client.

        Args:
            llm_config: Dict with keys ``enabled``, ``provider`` and
                ``model`` (e.g. the ``llm`` section of
                stockei_config.yaml). Defaults to disabled.
        """
        self.config = llm_config or {}
        self.enabled: bool = bool(self.config.get("enabled", False))
        self.provider: str = self.config.get("provider", "openai")
        self.model: str = self.config.get("model", "gpt-4o-mini")
        logger.info("LLMClient initialized (enabled=%s, provider=%s, "
                    "model=%s)", self.enabled, self.provider, self.model)

    def complete(self, prompt: str) -> str:
        """
        Produce a completion for a prompt.

        When LLM is disabled, returns a deterministic stub response with
        a warning marker. When enabled, tries the configured provider
        (currently ``openai``) with a friendly error if the SDK or API
        key is missing.

        Args:
            prompt: The prompt text.

        Returns:
            Completion text (stub or real).
        """
        if not self.enabled:
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
            logger.info("LLMClient: returning stub completion (%s)", digest)
            return (f"[STUB LLM - llm.enabled=false] Resposta deterministica "
                    f"para o prompt (hash {digest}): "
                    f"'{prompt[:120]}'")
        if self.provider != "openai":
            return (f"[LLM ERROR] Provider '{self.provider}' nao suportado. "
                    f"Use provider 'openai' ou desative o LLM.")
        try:
            import openai  # noqa: PLC0415
        except ImportError:
            logger.warning("LLMClient: openai package not installed")
            return ("[LLM ERROR] Pacote 'openai' nao instalado. "
                    "Instale com 'pip install openai' ou defina "
                    "llm.enabled=false.")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("LLMClient: OPENAI_API_KEY not set")
            return ("[LLM ERROR] Variavel OPENAI_API_KEY nao definida. "
                    "Defina a chave ou use llm.enabled=false para o modo "
                    "stub.")
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.error("LLMClient: API call failed: %s", exc)
            return f"[LLM ERROR] Falha na chamada ao provedor: {exc}"
