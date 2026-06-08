# =============================================================================
# INTER-CODER-RELIABILITY: Spalte "approved"
# Methoden: Cohen's Kappa, Krippendorff's Alpha, Gwet's AC1, Scott's Pi
# Coder A: climate_emergency_corrected(A).xlsx
# Coder D: climate_emergency(D).xlsx
# =============================================================================
# Benötigte Pakete: irr, irrCAC, readxl, dplyr, janitor, stringr
# Installation (einmalig): install.packages(c("irr","irrCAC","readxl","dplyr","janitor","stringr"))
# =============================================================================

library(readxl)
library(dplyr)
library(janitor)
library(stringr)
library(irr)      # kappa2(), kripp.alpha(), agree()
library(irrCAC)   # gwet.ac1(), scott.pi() – robuste Alternativen zu Kappa


# =============================================================================
# SCHRITT 1: Daten einlesen
# =============================================================================
# Wir lesen beide Datensätze wie gehabt mit read_excel() ein.
# clean_names() aus {janitor} normalisiert Spaltennamen (Leerzeichen → _,
# Großbuchstaben → Kleinbuchstaben), sodass sie programmatisch sicher nutzbar sind.

df_A <- read_excel("climate_emergency_corrected(A).xlsx", sheet = 1) %>%
  clean_names()

df_D <- read_excel("climate_emergency(D).xlsx", sheet = 1) %>%
  clean_names()


# =============================================================================
# SCHRITT 2: Relevante Spalten extrahieren und bereinigen
# =============================================================================
# Wir benötigen municipality_name (als Schlüssel für den Join) sowie approved
# (die zu vergleichende Variable). as.character() stellt sicher, dass keine
# unerwarteten Datentypen (Faktoren, Zahlen) den Vergleich verfälschen.
# str_trim() entfernt führende/nachfolgende Leerzeichen – ein häufiges Problem
# bei manuell erfassten Daten. na_if() markiert leere Strings explizit als NA,
# sodass sie später beim NA-Filter sauber herausgefiltert werden.
# str_to_lower() normalisiert Groß-/Kleinschreibung, da "yes", "Yes" und "YES"
# sonst als unterschiedliche Kategorien behandelt würden.

df_A_icr <- df_A %>%
  transmute(
    municipality_name = as.character(municipality_name),
    ags               = as.character(ags),
    approved          = as.character(approved)
  ) %>%
  mutate(
    municipality_name = str_trim(municipality_name),
    ags               = str_pad(str_trim(ags), width = 8, side = "left", pad = "0"),
    approved          = str_trim(str_to_lower(approved)),
    municipality_name = na_if(municipality_name, ""),
    ags               = na_if(ags, ""),
    approved          = na_if(approved, "")
  )

df_D_icr <- df_D %>%
  transmute(
    municipality_name = as.character(municipality_name),
    ags               = as.character(ags),
    approved          = as.character(approved)
  ) %>%
  mutate(
    municipality_name = str_trim(municipality_name),
    ags               = str_pad(str_trim(ags), width = 8, side = "left", pad = "0"),
    approved          = str_trim(str_to_lower(approved)),
    municipality_name = na_if(municipality_name, ""),
    ags               = na_if(ags, ""),
    approved          = na_if(approved, "")
  )


# =============================================================================
# SCHRITT 3: Duplikate in df_D behandeln
# =============================================================================
# df_D enthält ca. 100 doppelte Gemeindenamen. Das ist ein konzeptuelles
# Problem: Wenn eine Gemeinde mehrfach vorkommt (z.B. weil sie auf Gemeinde-
# UND Kreisebene erfasst wurde), erzeugt ein inner_join Kreuzprodukt-Zeilen,
# was die ICR-Berechnung verzerrt. Wir zeigen BEIDE Varianten:
#
# Variante A (konservativ): Nur den ERSTEN Treffer pro Gemeinde behalten.
#   → Vorteil: saubere 1:1-Paarung, klarer interpretierbarer Kappa-Wert.
#   → Nachteil: wir verlieren Information über Mehrfachkodierungen.
#
# Variante B (transparent): Alle Zeilen behalten, Duplikatanzahl dokumentieren.
#   → Vorteil: kein Datenverlust.
#   → Nachteil: mehrfache Paarungen mit demselben Coder-A-Wert erhöhen
#     künstlich die Fallzahl und können Kappa verzerren.
#
# Empfehlung für die Publikation: Variante A mit Fußnote, dass df_D
# Duplikate enthielt und diese vor dem Vergleich entfernt wurden.

n_dup_A <- sum(duplicated(df_A_icr$municipality_name, incomparables = NA))
n_dup_D <- sum(duplicated(df_D_icr$municipality_name, incomparables = NA))
cat(sprintf("Duplikate municipality_name: Coder A = %d, Coder D = %d\n",
            n_dup_A, n_dup_D))

# Variante A (empfohlen): Duplikate in D entfernen
df_D_icr_dedup <- df_D_icr %>%
  filter(!is.na(municipality_name)) %>%
  distinct(municipality_name, .keep_all = TRUE)  # erste Zeile pro Gemeinde behalten

cat(sprintf("df_D nach Dedup: %d Zeilen (vorher: %d)\n",
            nrow(df_D_icr_dedup), nrow(df_D_icr)))


# =============================================================================
# SCHRITT 4: Datensätze zusammenführen (inner_join)
# =============================================================================
# Wir verwenden inner_join() auf municipality_name als Schlüssel – analog zur
# AGS-ICR. inner_join() behält nur jene Gemeinden, die bei BEIDEN Codern
# vorhanden sind. left_join() oder full_join() würden NAs für fehlende Werte
# erzeugen, was die Kappa-Berechnung (die paarweise vollständige Werte
# voraussetzt) erschwert.
#
# Wichtiger Hinweis: Der inner_join misst die ICR nur auf dem GEMEINSAMEN
# Subset beider Codierungen. Die Differenz zwischen df_A (289 Fälle) und
# df_D (768 Fälle) – ca. 400 Fälle Unterschied – spiegelt sich nicht im
# Kappa-Wert wider. Dieser Unterschied ist jedoch inhaltlich bedeutsam:
# Er zeigt, dass beide Coder sehr unterschiedliche Einschlusskriterien
# (welche Fälle zählen überhaupt?) angewendet haben. Das ist eine eigene
# Dimension der ICR, die über den Kappa-Wert hinausgeht (→ siehe Schritt 8).

merged_approved <- inner_join(
  df_A_icr %>% rename(approved_A = approved, ags_A = ags),
  df_D_icr_dedup %>% rename(approved_D = approved, ags_D = ags),
  by = "municipality_name"
)

cat(sprintf("\nGemeinsame Fälle nach inner_join: %d\n", nrow(merged_approved)))


# =============================================================================
# SCHRITT 5: Nur vollständige Paare behalten
# =============================================================================
# Kappa (wie auch alle anderen hier berechneten Maße) benötigt paarweise
# vollständige Beobachtungen – ein fehlender Wert bei einem der beiden Coder
# macht das Paar unbrauchbar für die Berechnung. Wir dokumentieren, wie viele
# Paare aufgrund fehlender approved-Werte entfernt werden.

merged_approved_clean <- merged_approved %>%
  filter(!is.na(approved_A), !is.na(approved_D))

n_removed <- nrow(merged_approved) - nrow(merged_approved_clean)
cat(sprintf("Entfernte Paare wegen NA in 'approved': %d\n", n_removed))
cat(sprintf("Verbleibende Paare für ICR: %d\n\n", nrow(merged_approved_clean)))


# =============================================================================
# SCHRITT 6: Kontingenztabelle – deskriptiver Überblick
# =============================================================================
# Bevor wir ICR-Maße berechnen, schauen wir uns die Rohstruktur der
# Übereinstimmungen an. Die Kontingenztabelle (auch Konfusionsmatrix genannt)
# zeigt: Wie oft stimmten beide zu? Wie oft war A "yes" und D "no"?
# Diese Matrix ist die Grundlage aller nachfolgenden Maße.
#
# Außerdem prüfen wir die Randverteilungen: Wenn eine Kategorie (z.B. "yes")
# bei beiden Codern sehr häufig ist (Prävalenz-Problem), kann Kappa
# systematisch unterschätzt werden – dazu mehr in Schritt 9.

cat("=== Kontingenztabelle (Coder A = Zeilen, Coder D = Spalten) ===\n")
conf_matrix <- table(approved_A = merged_approved_clean$approved_A,
                     approved_D = merged_approved_clean$approved_D)
print(conf_matrix)
cat("\n")

# Randverteilungen
cat("Randverteilung Coder A:\n")
print(prop.table(table(merged_approved_clean$approved_A)) * 100)
cat("\nRandverteilung Coder D:\n")
print(prop.table(table(merged_approved_clean$approved_D)) * 100)
cat("\n")


# =============================================================================
# SCHRITT 7a: Einfache prozentuale Übereinstimmung (Percentage Agreement)
# =============================================================================
# Zum Vergleich berechnen wir zunächst das simple Percentage Agreement –
# also den Anteil der Paare, bei denen beide Coder denselben Wert vergaben.
# Dieses Maß ist leicht interpretierbar, berücksichtigt aber NICHT, wie viel
# Übereinstimmung allein durch Zufall zu erwarten wäre. Es überschätzt die
# "echte" Übereinstimmung, wenn eine Kategorie sehr häufig ist.
# Deshalb verwenden wir es hier nur als Referenzpunkt, nicht als primäres Maß.

pa_result <- irr::agree(data.frame(merged_approved_clean$approved_A,
                                   merged_approved_clean$approved_D))
cat("=== Percentage Agreement (nur als Referenz) ===\n")
print(pa_result)
cat("\n")


# =============================================================================
# SCHRITT 7b: Cohen's Kappa
# =============================================================================
# Cohen's Kappa (1960) ist das Standardmaß für nominale ICR bei zwei Codern.
# Es korrigiert die beobachtete Übereinstimmung um die zufällig zu erwartende
# Übereinstimmung (basierend auf den Randverteilungen beider Coder):
#
#   κ = (P_o − P_e) / (1 − P_e)
#
#   P_o = beobachtete Übereinstimmung
#   P_e = zufällig erwartete Übereinstimmung
#
# Interpretation nach Landis & Koch (1977):
#   < 0.00  = schlechter als Zufall
#   0.00–0.20 = slight (gering)
#   0.21–0.40 = fair (ausreichend)
#   0.41–0.60 = moderate (mäßig)
#   0.61–0.80 = substantial (beachtlich)
#   0.81–1.00 = almost perfect (fast perfekt)
#
# weighted = "unweighted": wir behandeln "yes" vs "no" als nominale Kategorien
# ohne Ordnung. Bei ordinalem approved würde man weighted = "quadratic" wählen.

kappa_result <- irr::kappa2(
  data.frame(merged_approved_clean$approved_A,
             merged_approved_clean$approved_D),
  weight = "unweighted"
)

cat("=== Cohen's Kappa ===\n")
print(kappa_result)
cat(sprintf("Interpretation: κ = %.4f → %s\n\n",
            kappa_result$value,
            dplyr::case_when(
              kappa_result$value < 0    ~ "schlechter als Zufall",
              kappa_result$value < 0.21 ~ "slight (gering)",
              kappa_result$value < 0.41 ~ "fair (ausreichend)",
              kappa_result$value < 0.61 ~ "moderate (mäßig)",
              kappa_result$value < 0.81 ~ "substantial (beachtlich)",
              TRUE                      ~ "almost perfect (fast perfekt)"
            )))


# =============================================================================
# SCHRITT 7c: Krippendorff's Alpha
# =============================================================================
# Krippendorff's Alpha (Hayes & Krippendorff 2007) ist in vielerlei Hinsicht
# flexibler als Cohen's Kappa:
#
#   1. Skalenniveau: Es funktioniert für nominale, ordinale, intervall- und
#      ratioskalierte Daten (hier: "nominal").
#   2. Fehlende Werte: Alpha kann mit NAs umgehen – kein listenweiser Ausschluss
#      nötig. (Für uns weniger relevant, da wir schon gefiltert haben.)
#   3. Mehr als 2 Coder: Alpha lässt sich auf beliebig viele Coder erweitern.
#      Cohen's Kappa ist streng auf 2 Coder beschränkt.
#   4. Konservativer: Alpha gilt als strenger und damit fairer, da es keinen
#      Fehler für zufällige Übereinstimmung "einpreist".
#
# Richtwert: Krippendorff empfiehlt α ≥ 0.80 für substanzielle Schlüsse,
# α ≥ 0.67 als unterste Grenze für provisorische Schlüsse.
#
# Eingabe: Matrix mit 2 Zeilen (eine je Coder) und n Spalten (eine je Fall).
# Die Werte müssen numerisch oder als Faktor vorliegen; bei nominaler Skala
# wird 0/1 für no/yes codiert, da kripp.alpha() mit Zeichenketten arbeiten kann.

ratings_matrix <- rbind(
  merged_approved_clean$approved_A,
  merged_approved_clean$approved_D
)
# =============================================================================
# SCHRITT 7c (korrigiert): Krippendorff's Alpha
# =============================================================================
# kripp.alpha() aus {irr} erwartet eine numerische Matrix. Übergibt man
# Zeichenketten wie "yes"/"no", versucht R sie intern per as.numeric()
# umzuwandeln – was naturgemäß fehlschlägt und NAs erzeugt. Die Warnung
# "NAs durch Umwandlung erzeugt" signalisiert genau dieses Problem.
#
# Lösung: Wir kodieren "yes" → 1 und "no" → 0 explizit um, bevor wir die
# Matrix bauen. Das ist bei nominaler Skala vollständig äquivalent –
# Alpha ist invariant gegenüber der Wahl der numerischen Codes, solange
# die Kategorien konsistent kodiert sind.

recode_approved <- function(x) {
  dplyr::case_when(
    x == "yes" ~ 1L,
    x == "no"  ~ 0L,
    TRUE       ~ NA_integer_   # alle anderen Werte explizit als NA
  )
}

ratings_matrix <- rbind(
  recode_approved(merged_approved_clean$approved_A),
  recode_approved(merged_approved_clean$approved_D)
)

# Sicherheitscheck: keine unerwarteten NAs nach der Umkodierung?
n_na_after <- sum(is.na(ratings_matrix))
if (n_na_after > 0) {
  cat(sprintf("⚠ %d NA(s) in der Ratings-Matrix – prüfen Sie die Rohdaten.\n",
              n_na_after))
} else {
  cat("✓ Ratings-Matrix vollständig (keine NAs).\n")
}

alpha_result <- irr::kripp.alpha(ratings_matrix, method = "nominal")

alpha_result <- irr::kripp.alpha(ratings_matrix, method = "nominal")

cat("=== Krippendorff's Alpha (nominal) ===\n")
print(alpha_result)
cat(sprintf("Interpretation: α = %.4f → %s\n\n",
            alpha_result$value,
            dplyr::case_when(
              alpha_result$value < 0.67 ~ "zu niedrig für verlässliche Schlüsse",
              alpha_result$value < 0.80 ~ "provisorisch akzeptabel (≥ 0.67)",
              TRUE                      ~ "substanziell akzeptabel (≥ 0.80)"
            )))


# =============================================================================
# SCHRITT 7d: Gwet's AC1
# =============================================================================
# Gwet's AC1 (Gwet 2008) ist eine Alternative zu Kappa, die das sogenannte
# "Kappa-Paradox" überwindet (dazu mehr in Schritt 9). AC1 berechnet die
# zufällig erwartete Übereinstimmung P_e anders als Kappa: Es geht nicht von
# den empirischen Randverteilungen aus, sondern von der Annahme, dass beide
# Coder zufällig aus allen Kategorien wählen – und berücksichtigt dabei die
# Schwierigkeit der Kodierung.
#
# Wann AC1 bevorzugen? Wenn eine Kategorie bei beiden Codern sehr häufig
# (> 70%) oder sehr selten (< 30%) ist. In solchen Situationen kann Kappa
# niedrig erscheinen, obwohl die faktische Übereinstimmung hoch ist.
# AC1 ist dann stabiler und interpretationsfreundlicher.

# irrCAC erwartet einen data.frame mit einer Spalte je Coder
ratings_df <- data.frame(
  CoderA = merged_approved_clean$approved_A,
  CoderD = merged_approved_clean$approved_D
)

ac1_result <- irrCAC::gwet.ac1.raw(ratings_df)

cat("=== Gwet's AC1 ===\n")
cat(sprintf(
  "Beobachtete Übereinstimmung (pa):       %.1f%%\n",
  ac1_result$est$pa * 100
))
cat(sprintf(
  "Zufällig erwartete Übereinstimmung (pe): %.1f%%\n",
  ac1_result$est$pe * 100
))
cat(sprintf(
  "AC1-Koeffizient:                         %.4f\n",
  ac1_result$est$coeff.val
))
cat(sprintf(
  "Standardfehler:                          %.4f\n",
  ac1_result$est$coeff.se
))
cat(sprintf(
  "95%%-Konfidenzintervall:                  %s\n",
  ac1_result$est$conf.int
))
cat(sprintf(
  "p-Wert:                                  %s\n",
  ifelse(ac1_result$est$p.value == 0, "< 0.001", round(ac1_result$est$p.value, 4))
))
cat(sprintf(
  "Analysierte Paare (n):                   %d\n",
  ac1_result$est$tot.obs
))
cat(sprintf(
  "Interpretation: AC1 = %.3f liegt im Bereich '%s'\n",
  ac1_result$est$coeff.val,
  dplyr::case_when(
    ac1_result$est$coeff.val < 0.21 ~ "slight (gering)",
    ac1_result$est$coeff.val < 0.41 ~ "fair (ausreichend)",
    ac1_result$est$coeff.val < 0.61 ~ "moderate (mäßig)",
    ac1_result$est$coeff.val < 0.81 ~ "substantial (beachtlich)",
    TRUE                             ~ "almost perfect (fast perfekt)"
  )
))
cat(paste(rep("-", 55), collapse = ""), "\n\n")

# =============================================================================
# SCHRITT 7e: Scott's Pi
# =============================================================================
# Scott's Pi (Scott 1955) ist historisch Kappa sehr ähnlich, unterscheidet
# sich aber in der Berechnung von P_e: Während Kappa die Randverteilungen
# beider Coder SEPARAT berücksichtigt (und damit implizit annimmt, dass Coder
# unterschiedliche Basisraten haben können), mittelt Scott's Pi die
# Randverteilungen beider Coder. Das macht Pi symmetrischer, aber auch
# weniger flexibel als Kappa. In der Praxis sind die Unterschiede zwischen
# Kappa und Pi oft klein – wenn sie stark divergieren, ist das ein Zeichen
# dafür, dass die Coder sehr unterschiedliche Basisraten haben.

# scott2.table erwartet eine Kontingenztabelle als Input,
# keine Rohdaten. Wir erstellen sie aus ratings_df mit table().
pi_val   <- as.numeric(pi_result$coeff.val)
pi_label <- ifelse(pi_val < 0.21, "slight (gering)",
                   ifelse(pi_val < 0.41, "fair (ausreichend)",
                          ifelse(pi_val < 0.61, "moderate (mäßig)",
                                 ifelse(pi_val < 0.81, "substantial (beachtlich)",
                                        "almost perfect (fast perfekt)"))))

cat(sprintf("Interpretation: Pi = %.3f liegt im Bereich '%s'\n\n",
            pi_val, pi_label))


# =============================================================================
# SCHRITT 8: Zusammenfassung aller Maße
# =============================================================================
# Wir fassen alle berechneten Maße in einer übersichtlichen Tabelle zusammen.
# Das erleichtert den Vergleich und hilft bei der Entscheidung, welches Maß
# im Methodenteil der Publikation berichtet wird.

cat("=== ZUSAMMENFASSUNG: ICR-KENNZAHLEN FÜR 'approved' ===\n")
cat(sprintf("Analysierte Paare (n):         %d\n", nrow(merged_approved_clean)))
cat(sprintf("Percentage Agreement:           %.2f%%\n", pa_result$value))
cat(sprintf("Cohen's Kappa:                  %.4f  (p = %.4f)\n",
            kappa_result$value, kappa_result$p.value))
cat(sprintf("Krippendorff's Alpha:           %.4f\n", alpha_result$value))
cat(sprintf("Gwet's AC1:                     %.4f\n", ac1_result$est$coeff.val))
cat(sprintf("Scott's Pi:                     %.4f\n\n", pi_result$coeff.val))

# =============================================================================
# SCHRITT 9: Methodenkritik – das Kappa-Paradox und Prävalenz-Problem
# =============================================================================
# Cohen's Kappa hat eine bekannte Schwäche: Das "Kappa-Paradox" (Feinstein &
# Cicchetti 1990). Wenn eine Kategorie sehr häufig ist (hohe Prävalenz), kann
# Kappa einen täuschend niedrigen Wert liefern, obwohl die faktische
# Übereinstimmung hoch ist. Umgekehrt kann Kappa hoch sein, obwohl die Coder
# in den seltenen Kategorien kaum übereinstimmen.
#
# Konkret für unsere Daten:
# - "no" ist bei beiden Codern deutlich häufiger als "yes"
# - Bei stark ungleichen Randverteilungen unterschätzt Kappa die Reliabilität
# - In diesem Fall ist Gwet's AC1 die robustere Wahl
#
# Wir prüfen die Prävalenz und geben eine Empfehlung:

prev_A <- mean(merged_approved_clean$approved_A == "yes", na.rm = TRUE)
prev_D <- mean(merged_approved_clean$approved_D == "yes", na.rm = TRUE)
cat(sprintf("Prävalenz 'yes': Coder A = %.1f%%, Coder D = %.1f%%\n",
            prev_A * 100, prev_D * 100))

if (abs(prev_A - 0.5) > 0.2 | abs(prev_D - 0.5) > 0.2) {
  cat("⚠ Prävalenz deutlich von 50%% entfernt → Kappa-Paradox möglich.\n")
  cat("  Empfehlung: Gwet's AC1 als primäres Maß berichten,\n")
  cat("  Cohen's Kappa als Ergänzung angeben.\n")
} else {
  cat("✓ Prävalenz nahe 50%% → Kappa-Paradox unwahrscheinlich.\n")
  cat("  Cohen's Kappa als primäres Maß geeignet.\n")
}


# =============================================================================
# SCHRITT 10: Scope-Problem dokumentieren
# =============================================================================
# Ein letzter, oft übersehener Aspekt der ICR ist die Übereinstimmung bei
# der FALLIDENTIFIKATION: Welche Fälle wurden überhaupt kodiert?
# df_A hat 289 Zeilen, df_D hat 768. Der inner_join umfasst nur 169 gemeinsame
# Gemeinden. Das bedeutet: 120 Gemeinden aus A wurden in D nicht erfasst,
# und 599 Gemeinden aus D wurden in A nicht erfasst.
#
# Diese Diskrepanz liegt nicht in der Kodierung (approved ja/nein), sondern
# in der Definition des Samples (welche Gemeinden kommen überhaupt in Frage).
# Das ist die sogenannte "case identification reliability" oder Erfassungsrate.
# Sie ist durch Kappa nicht abgebildet und sollte im Methodenteil separat
# diskutiert werden.

n_only_A  <- nrow(df_A_icr %>% filter(!is.na(municipality_name))) -
  nrow(merged_approved_clean)
n_only_D  <- nrow(df_D_icr_dedup %>% filter(!is.na(municipality_name))) -
  nrow(merged_approved_clean)

cat(sprintf("\n=== SCOPE (Fallidentifikation) ===\n"))
cat(sprintf("Gemeinden nur bei Coder A:  %d\n", n_only_A))
cat(sprintf("Gemeinden nur bei Coder D:  %d\n", n_only_D))
cat(sprintf("Gemeinden bei beiden:       %d\n", nrow(merged_approved_clean)))
cat(sprintf("Erfassungsrate (Overlap):   %.1f%% von Coder A, %.1f%% von Coder D\n",
            nrow(merged_approved_clean) /
              nrow(filter(df_A_icr, !is.na(municipality_name))) * 100,
            nrow(merged_approved_clean) /
              nrow(filter(df_D_icr_dedup, !is.na(municipality_name))) * 100))
cat("\nHinweis: Der geringe Overlap deutet auf unterschiedliche Einschluss-\n")
cat("kriterien hin (z.B. Kreisebene vs. Gemeindeebene, Zeitraum, Quellen).\n")
cat("Dies ist ein konzeptuelles Problem, das durch ICR-Maße allein nicht\n")
cat("gelöst werden kann – es erfordert eine Nachkodier-Runde mit explizitem\n")
cat("Codebuch.\n")
