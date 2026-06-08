# =============================================================================
# INTER-CODER RELIABILITY checks for Climate Emergency data
# Method: Percentage Agreement
# Coder A: climate_emergency_cA.xlsx
# Coder B: climate_emergency_cB.xlsx
# =============================================================================
# Required packages: readxl, dplyr, janitor, stringr
# install.packages(c("readxl","dplyr","janitor","stringr"))
# =============================================================================

library(readxl)
library(dplyr)
library(janitor)
library(stringr)


# =============================================================================
# SCHRITT 1: Daten einlesen
# =============================================================================
# Wir lesen die korrigierte Fassung von Coder A ein. Eine erste Berechnung
# mit der ursprünglichen Datei (climate_emergency_final(A).xlsx) ergab ein
# Percentage Agreement von nur 46.7% – die Ursache lag nicht in echter
# Uneinigkeit, sondern in einem Formatierungsfehler: Die AGS-Codes in df_A
# fehlten führende Nullen (z.B. "5334002" statt "05334002"). Nach Korrektur
# und erneuter Berechnung stieg das Agreement auf 99.4%.
# clean_names() normalisiert Spaltennamen (Leerzeichen → _, Großbuchstaben
# → Kleinbuchstaben) für sicheres programmatisches Arbeiten.

df_A <- read_excel("climate_emergency_corrected(A).xlsx", sheet = 1) %>%
  clean_names()

df_D <- read_excel("climate_emergency(D).xlsx", sheet = 1) %>%
  clean_names()


# =============================================================================
# SCHRITT 2: Relevante Spalten extrahieren und bereinigen
# =============================================================================
# transmute() wählt nur die benötigten Spalten aus und verwirft alle anderen.
# as.character() verhindert, dass numerisch eingelesene AGS-Codes (ohne
# führende Null) als Zahlen behandelt werden.
# str_trim() entfernt Leerzeichen, na_if() markiert leere Strings als NA.
# str_pad() ist die entscheidende Korrektur: AGS-Codes sind immer 8-stellig.
# Excel liest "05334002" manchmal als Zahl 5334002 (ohne führende Null) –
# str_pad() stellt die korrekte 8-stellige Form wieder her. Ohne diese
# Korrektur würde kein einziger Code übereinstimmen, obwohl beide Coder
# dieselbe Gemeinde gemeint haben.

df_A_icr <- df_A %>%
  transmute(
    municipality_name = as.character(municipality_name),
    ags               = as.character(ags)
  ) %>%
  mutate(
    municipality_name = str_trim(municipality_name),
    ags               = str_trim(ags),
    municipality_name = na_if(municipality_name, ""),
    ags               = na_if(ags, ""),
    ags               = str_pad(ags, width = 8, side = "left", pad = "0")
  )

df_D_icr <- df_D %>%
  transmute(
    municipality_name = as.character(municipality_name),
    ags               = as.character(ags)
  ) %>%
  mutate(
    municipality_name = str_trim(municipality_name),
    ags               = str_trim(ags),
    municipality_name = na_if(municipality_name, ""),
    ags               = na_if(ags, ""),
    ags               = str_pad(ags, width = 8, side = "left", pad = "0")
  )


# =============================================================================
# SCHRITT 3: Überblick und Duplikatprüfung
# =============================================================================
# Bevor wir zusammenführen, verschaffen wir uns einen Überblick über die
# Struktur beider Datensätze. Besonders wichtig: Duplikate in municipality_name.
# Eine Gemeinde kann mehrfach auftreten, wenn sie sowohl als Einzelgemeinde
# als auch als Teil eines Kreisbeschlusses kodiert wurde (z.B. Engelskirchen
# in df_A, fast 100 Gemeinden in df_D). Duplikate verfälschen den inner_join:
# Statt einer 1:1-Paarung entstehen Kreuzprodukte, die die Fallzahl künstlich
# erhöhen und das Agreement verzerren.

cat("=== Überblick ===\n")
cat(sprintf("Coder A: %d Zeilen, %d eindeutige Gemeinden\n",
            nrow(df_A_icr), n_distinct(df_A_icr$municipality_name, na.rm = TRUE)))
cat(sprintf("Coder D: %d Zeilen, %d eindeutige Gemeinden\n\n",
            nrow(df_D_icr), n_distinct(df_D_icr$municipality_name, na.rm = TRUE)))

dup_A <- df_A_icr %>% count(municipality_name) %>% filter(n > 1)
dup_D <- df_D_icr %>% count(municipality_name) %>% filter(n > 1)

cat(sprintf("Duplikate municipality_name: Coder A = %d, Coder D = %d\n\n",
            nrow(dup_A), nrow(dup_D)))


# =============================================================================
# SCHRITT 4: Duplikate entfernen
# =============================================================================
# Wir behalten pro Gemeinde nur die erste Zeile (distinct(.keep_all = TRUE)).
# Das ist die konservative Lösung: Wir vergleichen nur eindeutig zuordenbare
# Kodierungen. Alternativ könnte man alle Duplikate manuell prüfen und die
# inhaltlich passendste Zeile auswählen – das würde jedoch den Rahmen der
# automatisierten ICR-Berechnung sprengen und wird im Methodenteil als
# Limitation vermerkt.

df_A_icr_dedup <- df_A_icr %>%
  filter(!is.na(municipality_name)) %>%
  distinct(municipality_name, .keep_all = TRUE) %>%
  rename(ags_A = ags)

df_D_icr_dedup <- df_D_icr %>%
  filter(!is.na(municipality_name)) %>%
  distinct(municipality_name, .keep_all = TRUE) %>%
  rename(ags_D = ags)


# =============================================================================
# SCHRITT 5: Datensätze zusammenführen (inner_join)
# =============================================================================
# inner_join() auf municipality_name behält nur Gemeinden, die bei BEIDEN
# Codern vorhanden sind. Das ist der direkt vergleichbare Kern der Daten.
# Gemeinden, die nur ein Coder erfasst hat, fließen nicht in das
# Percentage Agreement ein – sie werden aber in Schritt 7 (Scope) separat
# dokumentiert, da auch die Frage "Welche Fälle wurden überhaupt kodiert?"
# eine eigene Dimension der ICR darstellt.

merged_ags <- inner_join(df_A_icr_dedup, df_D_icr_dedup, by = "municipality_name")

cat(sprintf("Gemeinsame Fälle nach inner_join: %d\n\n", nrow(merged_ags)))


# =============================================================================
# SCHRITT 6: Nur vollständige Paare behalten und Agreement berechnen
# =============================================================================
# Für das Percentage Agreement benötigen wir Paare, bei denen beide Coder
# einen AGS-Wert vergeben haben. Fehlende AGS bei einem der beiden Coder
# machen das Paar unbrauchbar für den Vergleich.
# Percentage Agreement = Anteil der Paare mit identischem AGS-Code.
# Es ist das geeignete Maß für die AGS-Spalte: Da der AGS ein eindeutiger
# Identifikator ist (entweder stimmt er überein oder nicht), gibt es keine
# "Grade" der Übereinstimmung – Cohen's Kappa wäre hier rechnerisch möglich,
# aber bei >400 Kategorien (eine je Gemeinde) wenig aussagekräftig.

merged_ags_clean <- merged_ags %>%
  filter(!is.na(ags_A), !is.na(ags_D)) %>%
  mutate(same_ags = ags_A == ags_D)

n_removed <- nrow(merged_ags) - nrow(merged_ags_clean)
cat(sprintf("Entfernte Paare wegen NA in 'ags': %d\n", n_removed))
cat(sprintf("Verbleibende Paare für ICR:        %d\n\n", nrow(merged_ags_clean)))

percentage_agreement <- mean(merged_ags_clean$same_ags) * 100

cat(sprintf("Percentage Agreement (AGS): %.2f%%\n", percentage_agreement))
cat(sprintf("Interpretation: Bei %.1f%% der gemeinsam kodierten Gemeinden\n",
            percentage_agreement))
cat(sprintf("vergaben beide Coder denselben AGS-Code.\n\n"))


# =============================================================================
# SCHRITT 7: Konfliktfälle exportieren
# =============================================================================
# Wir exportieren alle Paare mit abweichenden AGS-Codes als CSV. Das erlaubt
# eine manuelle Nachprüfung: Handelt es sich um echte Kodierungsfehler,
# oder um systematische Unterschiede (z.B. Gemeinde- vs. Kreisschlüssel)?

conflicts <- merged_ags_clean %>%
  filter(!same_ags) %>%
  select(municipality_name, ags_A, ags_D)

cat(sprintf("Konfliktfälle (abweichende AGS): %d\n", nrow(conflicts)))

if (nrow(conflicts) > 0) {
  write.csv(conflicts, "ags_conflicts.csv", row.names = FALSE)
  cat("→ Konfliktfälle gespeichert in: ags_conflicts.csv\n\n")
}


# =============================================================================
# SCHRITT 8: Scope – Fallidentifikation dokumentieren
# =============================================================================
# Das Percentage Agreement misst nur die Übereinstimmung im gemeinsamen
# Subset. Die Differenz zwischen df_A (~289 Fälle) und df_D (~768 Fälle)
# ist jedoch inhaltlich bedeutsam: Sie zeigt, dass beide Coder sehr
# unterschiedliche Einschlusskriterien angewendet haben. Diese Diskrepanz
# ist nicht durch das Agreement-Maß abgebildet und sollte im Methodenteil
# als "Case Identification Reliability" separat diskutiert werden.

n_only_A <- nrow(df_A_icr_dedup) - nrow(merged_ags_clean)
n_only_D <- nrow(df_D_icr_dedup) - nrow(merged_ags_clean)

cat("=== Scope (Fallidentifikation) ===\n")
cat(sprintf("Gemeinden nur bei Coder A:  %d\n", n_only_A))
cat(sprintf("Gemeinden nur bei Coder D:  %d\n", n_only_D))
cat(sprintf("Gemeinden bei beiden:       %d\n", nrow(merged_ags_clean)))
cat(sprintf("Overlap-Rate (von A):       %.1f%%\n",
            nrow(merged_ags_clean) / nrow(df_A_icr_dedup) * 100))
cat(sprintf("Overlap-Rate (von D):       %.1f%%\n\n",
            nrow(merged_ags_clean) / nrow(df_D_icr_dedup) * 100))
cat("Hinweis: Der geringe Overlap deutet auf unterschiedliche Einschluss-\n")
cat("kriterien hin (Kreisebene vs. Gemeindeebene, Zeitraum, Quellen).\n")
cat("Dies sollte im Methodenteil als Limitation berichtet werden.\n")

