from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from kiwipiepy import Kiwi

DEFAULT_STOPWORDS = {"하다", "되다", "있다", "없다", "이다", "그리고", "하지만", "그러나"}

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+")
_HASHTAG_RE = re.compile(r"#[\w가-힣]+")
_MENTION_RE = re.compile(r"@[\w가-힣]+")
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF]"
)
_LAUGH_RE = re.compile(r"[ㅋㅎ]{2,}")
_CRY_RE = re.compile(r"[ㅠㅜ]{2,}")


class KiwiTextMiner:
    def __init__(self, stopwords: Iterable[str] | None = None) -> None:
        # Kiwi 초기화가 실패하거나 무거울 수 있으므로 지연 로딩
        self._kiwi: Kiwi | None = None
        self.stopwords = set(stopwords or []).union(DEFAULT_STOPWORDS)

    @property
    def kiwi(self) -> Kiwi:
        if self._kiwi is None:
            self._kiwi = Kiwi()
        return self._kiwi

    def clean(self, text: str, options: Dict[str, any]) -> str:
        clean_text = text or ""
        clean_text = unicodedata.normalize("NFKC", clean_text)
        if options.get("remove_url", True):
            clean_text = _URL_RE.sub(" ", clean_text)
        if options.get("remove_email", True):
            clean_text = _EMAIL_RE.sub(" ", clean_text)
        if options.get("remove_hashtag", True):
            clean_text = _HASHTAG_RE.sub(" ", clean_text)
        if options.get("remove_mention", True):
            clean_text = _MENTION_RE.sub(" ", clean_text)
        if options.get("remove_emoji", True):
            clean_text = _EMOJI_RE.sub(" ", clean_text)
        if options.get("remove_laugh", True):
            clean_text = _LAUGH_RE.sub(" ", clean_text)
            clean_text = _CRY_RE.sub(" ", clean_text)
        if options.get("korean_only", True):
            allowed = "" if options.get("keep_number") else "0-9"
            allowed_eng = "a-zA-Z" if options.get("keep_english") else ""
            regex = fr"[^가-힣{allowed}{allowed_eng}\s]"
            clean_text = re.sub(regex, " ", clean_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return clean_text

    def tokenize(self, text: str, pos_mode: str) -> List[str]:
        tokens = self.kiwi.tokenize(text)
        if pos_mode == "noun":
            accepted = {"NNG", "NNP"}
        else:
            accepted = {"NNG", "NNP", "VA", "VV", "XR", "MAG"}
        return [t.form for t in tokens if t.tag in accepted]

    def simple_tokenize(self, text: str, min_len: int) -> List[str]:
        """Kiwi 대안: 정규식 기반 단순 한글 토큰화(의존성/세그폴트 대비)."""
        return re.findall(rf"[가-힣]{{{min_len},}}", text)

    def _filter_pure_korean(self, tokens: List[str], min_len: int = 2) -> Tuple[List[str], List[str]]:
        filtered: List[str] = []
        leaked: List[str] = []
        for tok in tokens:
            if re.match(r"^[ㅋㅎ]+$", tok) or re.match(r"^[ㅠㅜ]+$", tok):
                leaked.append(tok)
                continue
            if not re.match(r"^[가-힣]{" + str(min_len) + r",}$", tok):
                leaked.append(tok)
                continue
            filtered.append(tok)
        return filtered, leaked

    def build_tokens(
        self,
        df: pd.DataFrame,
        options: Dict[str, any],
        text_source: str = "both",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if df.empty:
            return df, df, df, df, df
        rows = []
        freq_counter: Counter[str] = Counter()
        doc_counter: defaultdict[str, int] = defaultdict(int)
        leaked_counter: Counter[str] = Counter()
        empty_clean_rows = []
        empty_token_rows = []
        analyzer = options.get("analyzer", "kiwi")
        for _, row in df.iterrows():
            if text_source == "title":
                base_text = row.get("Title", "")
            elif text_source == "full":
                base_text = row.get("Full Text", "")
            else:
                base_text = f"{row.get('Title','')} {row.get('Full Text','')}"
            clean_text = self.clean(str(base_text), options)
            try:
                if analyzer == "simple":
                    tokens_raw = [t for t in self.simple_tokenize(clean_text, options.get("min_length", 2))]
                else:
                    tokens_raw = [
                        t for t in self.tokenize(clean_text, options.get("pos", "noun")) if len(t) >= options.get("min_length", 2)
                    ]
            except Exception:
                # Kiwi 오류 발생 시 간단 토크나이저로 폴백해 크래시 방지
                tokens_raw = [t for t in self.simple_tokenize(clean_text, options.get("min_length", 2))]
            if options.get("stopwords"):
                user_stop = {w.strip() for w in options["stopwords"].splitlines() if w.strip()}
                stopset = self.stopwords.union(user_stop)
            else:
                stopset = self.stopwords
            custom_drop = {w.strip() for w in options.get("custom_drop", "").splitlines() if w.strip()}
            tokens_no_stop = [t for t in tokens_raw if t not in stopset and t not in custom_drop]
            if options.get("strict_korean_only", True):
                tokens, leaked = self._filter_pure_korean(tokens_no_stop, options.get("token_min_len", 2))
                leaked_counter.update(leaked)
            else:
                tokens = tokens_no_stop
            if not clean_text.strip():
                empty_clean_rows.append(row)
            if not tokens:
                empty_token_rows.append(row)
            freq_counter.update(tokens)
            for tok in set(tokens):
                doc_counter[tok] += 1
            rows.append(
                {
                    "key": row.get("key"),
                    "Date": row.get("Date"),
                    "period": row.get("period"),
                    "Page Type": row.get("Page Type"),
                    "clean_text": clean_text,
                    "tokens": tokens,
                }
            )
        tokens_df = pd.DataFrame(rows)
        freq_df = pd.DataFrame(
            [
                {"token": tok, "count": count, "doc_freq": doc_counter.get(tok, 0)}
                for tok, count in freq_counter.items()
                if count >= options.get("min_freq", 2)
            ]
        ).sort_values("count", ascending=False)
        top50_df = freq_df.head(50)
        tokens_df["month"] = pd.to_datetime(tokens_df["Date"], errors="coerce").dt.to_period("M").astype(str)
        monthly_top_df = (
            tokens_df.explode("tokens")
            .groupby(["month", "tokens"])
            .size()
            .reset_index(name="count")
            .sort_values(["month", "count"], ascending=[True, False])
        )
        monthly_top_df = monthly_top_df.groupby("month").head(20)
        audit_rows = []
        for tok, count in leaked_counter.most_common(100):
            leak_type = "LATIN"
            if re.search(r"[0-9]", tok):
                leak_type = "DIGIT"
            if re.search(r"[ㅋㅎ]+", tok):
                leak_type = "LAUGH"
            if re.search(r"[ㅠㅜ]+", tok):
                leak_type = "CRY"
            audit_rows.append({"token": tok, "count": count, "type": leak_type})
        audit_df = pd.DataFrame(audit_rows)
        empty_report_rows = []
        for r in empty_clean_rows:
            empty_report_rows.append(
                {
                    "key": r.get("key"),
                    "date": r.get("Date"),
                    "page_type": r.get("Page Type"),
                    "title": r.get("Title"),
                    "raw_snippet": str(r.get("Full Text", ""))[:120],
                    "clean_snippet": "",
                    "empty_clean": True,
                    "empty_token": False,
                    "reason_hint": "Clean text empty (non-korean/emoji removed)",
                }
            )
        for r in empty_token_rows:
            empty_report_rows.append(
                {
                    "key": r.get("key"),
                    "date": r.get("Date"),
                    "page_type": r.get("Page Type"),
                    "title": r.get("Title"),
                    "raw_snippet": str(r.get("Full Text", ""))[:120],
                    "clean_snippet": str(r.get("clean_text", ""))[:120],
                    "empty_clean": False,
                    "empty_token": True,
                    "reason_hint": "Tokens filtered out",
                }
            )
        empty_report_df = pd.DataFrame(empty_report_rows)
        return tokens_df, freq_df, top50_df, monthly_top_df, audit_df, empty_report_df
