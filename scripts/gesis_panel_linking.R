# Load required packages
library(dplyr)     # Data manipulation
library(sf)        # Spatial data handling
library(ggplot2)   # Visualization
library(patchwork) # Plot composition

# Load external helper scripts (custom functions)
source("./scripts/gxc_link_dwd.R")
source("./scripts/link_dwd_modules.R")

# Load file paths (not included in repo)
source("paths.R")

# Load synthetic dataset created earlier
gp_synth <- readRDS("./data/gesis_panel/gp_synth.rds")

# Load and prepare original geospatial coordinates
gp_coords <-
  haven::read_dta(gp_path) |>                      # Read Stata file
  dplyr::filter(gitter_id_1km != "NA") |>          # Remove missing IDs
  dplyr::mutate(
    x = extract_inspire_coordinates(gitter_id_1km)[[1]], # Extract longitude-like coordinate
    y = extract_inspire_coordinates(gitter_id_1km)[[2]]  # Extract latitude-like coordinate
  ) |>
  sf::st_as_sf(coords = c("x", "y"), crs = 3035) |>
  dplyr::mutate(date = "2024-12-13")               # Add reference date

# -------------------------
# INKAR socio-economic data
# -------------------------

inkar_data_alloc <-
  inkaR::get_inkar_data(
    c("303"),
    level = "GEM",
    year = "2020",
    format = "wide",
    lang = "en"
  ) |>
  dplyr::as_tibble() |>
  dplyr::transmute(
    ags = region_id,
    `Allocations for investment promotion measures` = `2020`
  )

inkar_data_new_heat <-
  inkaR::get_inkar_data(
    "56",
    level = "KRE",
    year = "2023",
    format = "wide",
    lang = "en"
  ) |>
  dplyr::as_tibble() |>
  dplyr::transmute(
    krs = region_id,
    `Residential buildings with renewable heating` = `2023`
  )

# -------------------------
# E-charging station data
# -------------------------

e_chargers <-
  readxl::read_xlsx(
    "./data/geospatial_data/e-chargers.xlsx",
    skip = 10
  ) |>
  dplyr::transmute(
    implementation_date = Inbetriebnahmedatum,
    lon = as.numeric(gsub(",", ".", Längengrad)),
    lat = as.numeric(gsub(",", ".", Breitengrad))
  ) |>
  sf::st_as_sf(coords = c("lon", "lat"), crs = 4326) |>
  sf::st_transform(3035)

# Filter chargers available up to reference date
e_chargers_2024 <- dplyr::filter(e_chargers, implementation_date <= "2024-12-13")

# -------------------------
# Link synthetic data to DWD climate data
# -------------------------

gp_synth_prec <-
  gxc_link_dwd(
    gp_synth,
    what = "precipitation",
    date_variable = "date",
    months = c(3, 4, 5),
    years_back = 10,
    buffers = 5000,
    reference_statistic = function(x) quantile(x, probs = 0.9, na.rm = TRUE),
    where_processed = "./tmp/",
    where_raw = "./tmp/",
    where_secret = "./tmp/"
  ) |>
  dplyr::rename(`Days of extreme precipitation` = 6)

gp_synth_temp <-
  gxc_link_dwd(
    gp_synth,
    what = "air_temperature_mean",
    date_variable = "date",
    months = c(3, 4, 5),
    years_back = 10,
    buffers = 10000,
    reference_statistic = function(x) quantile(x, probs = 0.9, na.rm = TRUE),
    where_processed = "./tmp/",
    where_raw = "./tmp/",
    where_secret = "./tmp/"
  ) |>
  dplyr::rename(`Days of extreme air temperatures` = 6)

# Merge climate variables into synthetic dataset
gp_synth <-
  dplyr::left_join(
    gp_synth_prec,
    gp_synth_temp |> sf::st_drop_geometry()
  )

# -------------------------
# Add INKAR socio-economic indicators
# -------------------------

gp_synth <-
  gp_synth |>
  dplyr::left_join(inkar_data_alloc, by = "ags") |>
  dplyr::mutate(krs = substr(ags, 1, 5)) |>
  dplyr::left_join(inkar_data_new_heat, by = "krs")

# -------------------------
# Add E-charging station density
# -------------------------

gp_synth <-
  gp_synth |>
  dplyr::mutate(
    `E-Charging Stations in 1000m` =
      sf::st_is_within_distance(gp_synth, e_chargers, dist = 1000) |>
      lengths()
  )

# -------------------------
# Repeat same linkage for original coordinates
# -------------------------

gp_coords_prec <-
  gxc_link_dwd(
    gp_coords,
    what = "precipitation",
    date_variable = "date",
    months = c(3, 4, 5),
    years_back = 10,
    buffers = 5000,
    reference_statistic = function(x) quantile(x, probs = 0.9, na.rm = TRUE),
    where_processed = "./tmp2/",
    where_raw = "./tmp/",
    where_secret = "./tmp2/"
  ) |>
  dplyr::rename(`Days of extreme precipitation` = 5)

gp_coords_temp <-
  gxc_link_dwd(
    gp_coords,
    what = "air_temperature_mean",
    date_variable = "date",
    months = c(3, 4, 5),
    years_back = 10,
    buffers = 10000,
    reference_statistic = function(x) quantile(x, probs = 0.9, na.rm = TRUE),
    where_processed = "./tmp2/",
    where_raw = "./tmp/",
    where_secret = "./tmp2/"
  ) |>
  dplyr::rename(`Days of extreme air temperatures` = 5)

# Merge climate variables into original dataset
gp_coords <-
  dplyr::left_join(
    gp_coords_prec,
    gp_coords_temp |> sf::st_drop_geometry()
  )

# -------------------------
# Add administrative and INKAR data
# -------------------------

gp_coords <-
  gp_coords |>
  sf::st_join(
    ffm::bkg_admin_archive(level = "gem", year = "2024") |>
      sf::st_transform(3035) |>
      dplyr::transmute(ags = AGS)
  ) |>
  dplyr::left_join(inkar_data_alloc, by = "ags") |>
  dplyr::mutate(krs = substr(ags, 1, 5)) |>
  dplyr::left_join(inkar_data_new_heat, by = "krs")

# Add E-charging station counts
gp_coords <-
  gp_coords |>
  dplyr::mutate(
    `E-Charging Stations in 1000m` =
      sf::st_is_within_distance(gp_coords, e_chargers, dist = 1000) |>
      lengths()
  )

# -------------------------
# Combine synthetic and original data for comparison
# -------------------------

combined_data <-
  dplyr::bind_rows(
    gp_synth |>
      dplyr::transmute(
        `Data Type` = "Synthetic Data",
        `Days of extreme precipitation`,
        `Days of extreme air temperatures`,
        `E-Charging Stations in 1000m`,
        `Allocations for investment promotion measures`,
        `Residential buildings with renewable heating`
      ),
    gp_coords |>
      dplyr::transmute(
        `Data Type` = "Original Data",
        `Days of extreme precipitation`,
        `Days of extreme air temperatures`,
        `E-Charging Stations in 1000m`,
        `Allocations for investment promotion measures`,
        `Residential buildings with renewable heating`
      )
  ) |>
  tidyr::pivot_longer(
    cols = c(
      `Days of extreme precipitation`,
      `Days of extreme air temperatures`,
      `E-Charging Stations in 1000m`,
      `Allocations for investment promotion measures`,
      `Residential buildings with renewable heating`
    ),
    names_to = "Spatial Indicator"
  )

# -------------------------
# Descriptive statistics
# -------------------------

combined_data_descriptives <-
  combined_data |>
  dplyr::group_by(`Data Type`, `Spatial Indicator`) |>
  sf::st_drop_geometry() |>
  dplyr::summarise(
    Minimum = min(value, na.rm = TRUE),
    Maximum = max(value, na.rm = TRUE),
    Mean = mean(value, na.rm = TRUE),
    Median = median(value, na.rm = TRUE),
    SD = sd(value, na.rm = TRUE),
    `N Missing` = sum(is.na(value)),
    .groups = "drop"
  ) |>
  dplyr::arrange(`Spatial Indicator`)

# Compute relative differences between datasets
combined_data_descriptives <-
  combined_data_descriptives |>
  split(combined_data_descriptives$`Spatial Indicator`) |>
  lapply(function(x) {

    num_cols <- sapply(x, is.numeric)

    diff_row <-
      data.frame(
        `Data Type` = "",
        `Spatial Indicator` = "Difference in %",
        ((x[2, num_cols] - x[1, num_cols]) / x[1, num_cols]) * 100,
        check.names = FALSE
      )

    diff_row[is.nan(diff_row)] <- 0

    rbind(x, diff_row)
  }) |>
  do.call(rbind) |>
  tibble::as_tibble()

# -------------------------
# Visualization: distribution comparison
# -------------------------

figure_ori_synth_comparison <-
  combined_data |>
  dplyr::group_by(`Spatial Indicator`) |>
  dplyr::mutate(value = scale(value)) |>
  ggplot() +
  geom_density(
    aes(
      x = value,
      fill = `Data Type`
    ),
    alpha = 0.5
  ) +
  facet_wrap(~`Spatial Indicator`, ncol = 2) +
  scale_fill_viridis_d() +
  theme_bw() +
  theme(legend.position = c(0.75, 0.18)) +
  xlim(-2, 4) +
  ylab("Density") +
  xlab("Z-standardized values (synthetic vs original)")

# Save plot
ggsave(
  "./figures/figure_ori_synth_comparison.png",
  figure_ori_synth_comparison,
  dpi = 600,
  width = 8,
  height = 6
)
