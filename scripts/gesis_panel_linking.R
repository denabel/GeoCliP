library(ggplot2)  # Load ggplot2 for visualization
library(dplyr)   # Load dplyr for data manipulation
library(sf)      # Load sf for spatial data handling

# Source external R scripts for additional functions
source("./scripts/extract_inspire_coordinates.R")
source("./scripts/gxc_link_dwd.R")
source("./scripts/link_dwd_modules.R")

# Source external script containing file paths
source("./tmp/paths.R")

# Load synthetic dataset
# Created with external R package: https://github.com/StefanJuenger/geosynth
# Install with: remotes::install_github("StefanJuenger/geosynth")
gp_synth <- readRDS("./data/gesis_panel/gp_synth.rds") 

# Read geospatial coordinates from a Stata file and convert to spatial data
gp_coords <-
  haven::read_dta(gp_path) |> # Read Stata file
  dplyr::filter(gitter_id_1km != "NA") |> # Remove missing values
  dplyr::mutate(
    x = extract_inspire_coordinates(gitter_id_1km)[[1]], # Extract x-coordinates
    y = extract_inspire_coordinates(gitter_id_1km)[[2]]  # Extract y-coordinates
  ) |>
  sf::st_as_sf(coords = c("x", "y"), crs = 3035) |>  # Convert to spatial object (EPSG: 3035)
  dplyr::mutate(date = "2022-06-02")  # Add a reference date

# Link synthetic data with historical precipitation data
gp_synth <-
  gp_synth |> 
  gxc_link_dwd(
    what = "precipitation",  # Specify weather variable
    date_variable = "date",  # Define date column
    months = c(3, 4, 5),      # Select months (March, April, May)
    years_back = 10,          # Use data from the last 10 years
    buffers = 5000,           # Define a spatial buffer of 5 km
    reference_statistic = function(x) {quantile(x, probs = .9, na.rm = TRUE)}, # Compute 90th percentile
    where_processed = "./tmp/",
    where_raw = "./tmp/",
    where_secret = "./tmp/"
  ) |> 
  dplyr::rename(`Days of extreme precipitation` = 3)  # Rename column

# Link original geospatial data with precipitation data
gp_coords <-
  gp_coords |> 
  gxc_link_dwd(
    what = "precipitation",  # Specify weather variable
    date_variable = "date",  # Define date column
    months = c(3, 4, 5),      # Select months (March, April, May)
    years_back = 10,          # Use data from the last 10 years
    buffers = 5000,           # Define a spatial buffer of 5 km
    reference_statistic = function(x) {quantile(x, probs = .9, na.rm = TRUE)}, # Compute 90th percentile
    where_processed = "./tmp/",
    where_raw = "./tmp/",
    where_secret = "./tmp/"
  ) |> 
  dplyr::rename(`Days of extreme precipitation` = 5)  # Rename column

# Combine synthetic and original data for comparison
combined_data <-
  dplyr::bind_rows(
    gp_synth |> 
      dplyr::transmute(
        `Data Type` = "Synthetic Data",
        `Days of extreme precipitation`
      ),
    gp_coords |> 
      dplyr::transmute(
        `Data Type` = "Original Data",
        `Days of extreme precipitation`
      )
  )

# Compute descriptive statistics for both datasets
combined_data_descriptives <-
  combined_data |> 
  dplyr::group_by(`Data Type`) |> 
  sf::st_drop_geometry() |>  # Drop spatial attributes
  dplyr::summarise(
    Minimum = min(`Days of extreme precipitation`, na.rm = TRUE),
    Maximum = max(`Days of extreme precipitation`, na.rm = TRUE),
    Mean = mean(`Days of extreme precipitation`, na.rm = TRUE),
    Median = median(`Days of extreme precipitation`, na.rm = TRUE),
    SD = sd(`Days of extreme precipitation`, na.rm = TRUE)
  )

# Compute the difference between synthetic and original data
combined_data_descriptives <-
  dplyr::bind_rows(
    combined_data_descriptives,
    combined_data_descriptives |> 
      dplyr::select(-1) |>  # Remove Data Type column
      purrr::map_dfr(diff) |>  # Compute differences
      dplyr::mutate(`Data Type` = "Difference", .before = 1) 
  )

# Create density plot comparing synthetic and original data
figure_ori_synth_comparison <-
  ggplot(combined_data) +
  geom_density(
    aes(
      `Days of extreme precipitation`, 
      group = `Data Type`, 
      fill = `Data Type`
    ),
    alpha = 0.5, position = 'identity', color = NA
  ) +
  scale_fill_viridis_d() +  # Use Viridis color scale
  theme_bw() +  # Apply a clean theme
  ylab("Density")  # Label y-axis

# Save the figure as a high-resolution PNG file
ggsave(
  "./figures/figure_ori_synth_comparison.png", 
  figure_ori_synth_comparison, 
  dpi = 600,  # High resolution
  width = 8,  # Set width
  height = 4   # Set height
)
