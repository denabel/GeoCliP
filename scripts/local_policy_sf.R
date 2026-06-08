################################################################################
### Policy data wrangling ######################################################
################################################################################


# Packages ----------------------------------------------------------------

library(tidyverse)
library(readxl)
library(sf)
library(lubridate)


# Load data ---------------------------------------------------------------

# Policy database
local_policy <- read_excel("./data/local_policy/NKI_full_list_21022024.xlsx")


# Data cleaning -----------------------------------------------------------

# Policy database
# Drop irrelevant variables
local_policy <- local_policy |> 
  select(-c(Ressort, Referat, PT, `Arb.-Einh.`, `Ausführende Stelle`, 
            `Staat...11`, `Gemeindekennziffer...13`, `Stadt/Gemeinde...14`, 
            `Ort...15`, `Bundesland...16`, `Staat...17`, Verbundprojekt, 
            Förderart))

# Rename variables
local_policy <- local_policy |> 
  rename(
    recipient = Zuwendungsempfänger,
    municipality_code = `Gemeindekennziffer...7`,
    municipality_name = `Stadt/Gemeinde...8`,
    location = `Ort...9`,
    state = `Bundesland...10`,
    subject = Thema,
    funding_code = Leistungsplansystematik,
    funding_line = `Klartext Leistungsplansystematik`,
    start_date = `Laufzeit von`,
    end_date = `Laufzeit bis`,
    funding_sum = `Fördersumme in EUR`,
    funding_profile = Förderprofil
  )

# Convert date-variables to date-format
local_policy <- local_policy |> 
  mutate(
    start_date = dmy(start_date),
    end_date = dmy(end_date)
  )

# Explore policy data -----------------------------------------------------

# Subset to end of 2023
local_policy <- local_policy |> 
  filter(ymd(start_date) <= "2023-12-31")

# How many municipalities participated in NKI until end of 2023?
length(unique(local_policy$municipality_code))

summary(local_policy$funding_sum)

ggplot(data = local_policy, mapping = aes(x=start_date)) +
  geom_histogram(binwidth=182)

options(scipen = 999)
funding_hist <- ggplot(data = local_policy, mapping = aes(x=funding_sum)) +
  geom_histogram(binwidth=1000)+
  theme_bw()+
  xlim(0,500000)+
  labs(title = "Distribution of funding amount by project", 
       subtitle = "X-scale cut-off at 500,000 Euro",
       x = "Amount of funding in Euro",
       y = "Count")

# ggsave(funding_hist, filename = "./figures/funding_hist.png", dpi = 300,
#        width = 5, height = 3, units = "in")


# Georeferencing ----------------------------------------------------------

# Municipalities shapefiles
municipalities <- st_read("./data/gemeinden_utm32/vg250_ebenen_0101/VG250_GEM.shp") |> 
  select(AGS, GEN, BEZ, geometry) |> 
  mutate(
    AGS = str_pad(as.character(AGS), width = 8, pad = "0")
  )

# If AGS appears multiple times, dissolve geometries
municipalities <- municipalities |> 
  group_by(AGS) |> 
  summarise(
    GEN = first(GEN),
    BEZ = first(BEZ),
    geometry = st_union(geometry),
    .groups = "drop"
  )

# Standardize municipality ID in policy data
local_policy <- local_policy |> 
  mutate(
    municipality_code = str_pad(as.character(municipality_code), width = 8, pad = "0"),
    start_year = year(start_date)
  )

# Merge into full spatial panel
local_policy_sf <- local_policy %>%
  left_join(municipalities %>% select(AGS, geometry), by = c("municipality_code" = "AGS")) %>%
  st_as_sf(sf_column_name = "geometry", crs = st_crs(municipalities))

# Output this file if entire study range required


# Example for four study years --------------------------------------------

# Aggregate policy data by municipality-year

policy_muni_year <- local_policy |> 
  filter(start_year %in% 2008:2011) |> 
  group_by(municipality_code, start_year) |> 
  summarise(
    n_projects = n(),
    funding_sum_total = sum(funding_sum, na.rm = TRUE),
    funding_sum_mean = mean(funding_sum, na.rm = TRUE),
    .groups = "drop"
  )

years_to_plot <- 2008:2011

municipality_year_grid <- expand_grid(
  AGS = municipalities$AGS,
  start_year = years_to_plot
)

map_data <- municipality_year_grid |> 
  left_join(municipalities, by = "AGS") |> 
  left_join(
    policy_muni_year,
    by = c("AGS" = "municipality_code", "start_year" = "start_year")
  ) |> 
  mutate(
    n_projects = replace_na(n_projects, 0),
    funding_sum_total = replace_na(funding_sum_total, 0)
  ) |> 
  st_as_sf(sf_column_name = "geometry", crs = st_crs(municipalities))

ggplot(map_data) +
  geom_sf(aes(fill = n_projects), color = NA) +
  facet_wrap(~ start_year, ncol = 2) +
  scale_fill_viridis_c(
    option = "magma",
    name = "Projects"
  ) +
  theme_void() +
  labs(
    title = "NKI-funded local climate policy projects by municipality",
    subtitle = "Number of projects by start year, 2008–2011"
  )
