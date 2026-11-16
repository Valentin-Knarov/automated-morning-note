# Variante : morning note par tâche planifiée Claude

Le pipeline Python produit une note **factuelle** : chiffres, variations, alertes.
Le commentaire de marché (le *pourquoi* des mouvements) demande de lire l'actualité. Une tâche planifiée Claude peut le rédiger chaque matin.

## Mise en place
1. Dans Claude, crée une **tâche planifiée**, du lundi au vendredi vers 7h00 (heure de Paris).
2. Colle le prompt ci-dessous, en adaptant la watchlist.
3. Facultatif : copie le commentaire obtenu dans la note Python avec
   `python -m morning_note --commentary "…"`.

## Prompt

```
Tu prépares la morning note d'un desk de sales trading actions à Paris, pour des clients institutionnels.

Watchlist : LVMH, TotalEnergies, Sanofi, Airbus, BNP Paribas, Société Générale, Schneider Electric,
Capgemini, Kering, Stellantis, Soitec, Nexans.

1. Recherche les clôtures de la veille (CAC 40, Euro Stoxx 50, S&P 500, Nasdaq), l'évolution des
   futures européens ce matin, l'EUR/USD, le Brent et le taux US 10 ans.
2. Recherche les actualités des dernières 24 h sur chaque valeur de la watchlist (résultats,
   guidance, changements de recommandation d'analystes, opérations financières).
3. Repère l'agenda du jour : publications de résultats, statistiques macro (heure de Paris),
   banques centrales.

Rédige en français, en 250 mots maximum :
- « En bref » : 3 puces sur le contexte de marché ;
- « Valeurs à suivre » : 3 à 5 valeurs, une ligne chacune, avec le fait et sa source ;
- « Agenda » : les rendez-vous du jour avec l'heure.
Style de desk : phrases courtes, chiffres précis, aucune recommandation d'achat ou de vente.
Cite tes sources à la fin. Si une information n'est pas confirmée, ne l'inclus pas.
```
