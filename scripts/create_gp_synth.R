# Load required packages
library(dplyr)    # Data manipulation
library(geosynth)
library(ggplot2)  # Visualization
library(haven)    # Read Stata files
library(sf)       # Spatial data handling
library(tmap)
library(z22)

# Set seed for reproducibility
set.seed(4 + 8 + 15 + 16 + 23 + 42)

# Load external file with paths
source("paths.R")

# Read geospatial data from Stata file
gp_coords <-
  haven::read_dta(gp_path) |>
  dplyr::filter(gitter_id_1km != "NA") # Remove missing values

# Add coordinates and convert to spatial object
gp_coords <-
  gp_coords |>
  cbind(z22::z22_inspire_extract(gp_coords$gitter_id_1km)) |>
  sf::st_as_sf(coords = c("x", "y"), crs = 3035)

# Create sample frame
gp_frame <-
  geosynth::create_sample_frame(
    gp_coords,
    year = "2024",
    geo_unit = "regiostar17",
    inhabitants_threshold = 100000,
    minimum_sample_points = 20
  )

# Draw synthetic sample
gp_synth <- draw_sample(gp_frame)

# Shuffle points until minimum distance is reached
gp_synth_shuffled <-
  geosynth::shuffle_min_distance(
    gp_synth,
    gp_coords,
    min_km = 100
  )

# Calculate distances between real and synthetic points
distances_real_synth <-
  sf::st_distance(gp_coords, gp_synth_shuffled, by_element = TRUE) |>
  as.vector() |>
  tibble::as_tibble_col(column_name = "distances")

# Plot histogram of distances in kilometers
ggplot(distances_real_synth) +
  geom_histogram(aes(distances / 1000), bins = 500) +
  xlim(0, 1000)

# Summary statistics for distances in kilometers
mean(distances_real_synth$distances / 1000)

min(distances_real_synth$distances / 1000)

quantile(
  distances_real_synth$distances / 1000,
  probs = c(.001, 0.01, .1, .25, .5, .75, .9)
)

# Second round of synthesizing for geoclip paper

# Create new sample frame
gp_frame_double <-
  gp_synth |>
  geosynth::create_sample_frame(
    year = "2024",
    geo_unit = "regiostar17",
    inhabitants_threshold = 100000,
    minimum_sample_points = 10
  )

# Draw second synthetic sample
gp_synth_double <- draw_sample(gp_frame_double)

# Shuffle points again with minimum distance condition
gp_synth_double_shuffled <-
  geosynth::shuffle_min_distance(
    gp_synth_double,
    gp_coords,
    min_km = 100
  )

# Calculate distances again
distances_real_synth <-
  sf::st_distance(gp_coords, gp_synth_double_shuffled, by_element = TRUE) |>
  as.vector() |>
  tibble::as_tibble_col(column_name = "distances")

# Plot histogram of distances
ggplot(distances_real_synth) +
  geom_histogram(aes(distances / 1000), bins = 500) +
  xlim(0, 1000)

# Summary statistics
mean(distances_real_synth$distances / 1000)

min(distances_real_synth$distances / 1000)

quantile(
  distances_real_synth$distances / 1000,
  probs = c(.001, 0.01, .1, .25, .5, .75, .9)
)

# Prepare final RDS dataset
gp_synth_final_rds <-
  gp_synth_double |>
  dplyr::mutate(id = 1:dplyr::n()) |>
  dplyr::mutate(date = "2022-12-13") |>
  dplyr::select(id, date, ags, inspid1km)

# Prepare CSV dataset with coordinates
gp_synth_final_csv <-
  gp_synth_final_rds |>
  dplyr::mutate(
    x = sf::st_coordinates(gp_synth_final_rds)[,1],
    y = sf::st_coordinates(gp_synth_final_rds)[,2]
  ) |>
  sf::st_drop_geometry()

# Save datasets
saveRDS(gp_synth_final_rds, "./data/gesis_panel/gp_synth.rds")

write.csv(
  gp_synth_final_csv,
  "./data/gesis_panel/gp_synth.csv",
  row.names = FALSE
)

