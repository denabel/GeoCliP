# Load required libraries
library(dplyr)          # Data manipulation
library(exactextractr)  # For performing spatial extraction of raster data
library(ecmwfr)         # For downloading climate data from Copernicus Climate Data Store (C3S)
library(ggplot2)        # For data visualization
library(glue)           # For string interpolation
library(patchwork)      # For arranging multiple ggplot objects
library(purrr)          # For functional programming (e.g., map, walk)
library(R.utils)        # For handling file compression and decompression
library(terra)          # For raster data manipulation and processing
library(textworks)      # For advanced string manipulation
library(tidyr)          # For data tidying and reshaping

# Set up C3S API access key (requires user input)
ecmwfr::wf_set_key()  # Prompts user to enter the API key
user <- ""  # Enter your C3S user ID here

# List of ERA5 variables to process
era5_variables <- 
  c("2m_temperature", "total_precipitation", "10m_u_component_of_wind",
    "10m_v_component_of_wind")  # ERA5 climate variables of interest

# List of DWD variables to process
dwd_variables <- 
  c("air_temperature_mean", "precipitation")  # DWD climate variables of interest

# Function to calculate wind speed from U and V wind components
calculate_wind_speed <- function(x, y, name) {
  wind_speed <- sqrt(x^2 + y^2)  # Wind speed is the vector magnitude of U and V
  names(wind_speed) <- name     # Assign the provided name to the result
  wind_speed
}

# Helper function to set up DWD request grid
setup_dwd_request_grid <- function(indicator, years, months) {
  years <- sprintf("%d", years)  # Convert years to character format
  months <- sprintf("%02d", months)  # Pad months with leading zeros
  
  # Create a folder name for each month
  months_folder <-
    months |> 
    purrr::map(~dplyr::tibble(
      months = .x,
      months_folder = 
        glue::glue(
          "{.x}_{lubridate::month(as.numeric(.x), label = TRUE, locale = 'en')}"
        )
    )) |> 
    dplyr::bind_rows()
  
  # Combine all parameters into a grid of requests
  tidyr::expand_grid(indicator = indicator, years, months) |> 
    dplyr::left_join(months_folder, by = "months") |> 
    dplyr::group_split(dplyr::row_number()) |> 
    purrr::map(~dplyr::select(.x, -`dplyr::row_number()`))
}

# Load municipality shapefile and transform it to WGS84 coordinate reference system
municipality_shape <-
  sf::st_read("./data/gemeinden_utm32/vg250_ebenen_0101/VG250_GEM.shp") |> 
  sf::st_transform(4326)  # Transform to EPSG:4326 (latitude-longitude)

# Define the request parameters for downloading ERA5 monthly mean temperature data
era5_requests <- 
  era5_variables |> 
  purrr::map(~{
    list(
      dataset_short_name = "reanalysis-era5-land-monthly-means",  # ERA5 dataset
      variable = .x,                            # Variable of interest
      year = sprintf("%d", 2008:2023),          # Range of years
      month = sprintf("%02d", 1:12),            # All months of the year
      time = "00:00",                           # Time of day
      data_format = "grib",                     # Output format (GRIB)
      download_format = "unarchived",           # Download without compression
      area = c(55.06, 5.87, 47.27, 15.04),      # Geographical extent (Germany)
      target = glue::glue("era5_monthly_{.x}_2008_to_2023.grib") # File name
    )
  })

# Define the request parameters for downloading DWD data
dwd_requests <-
  dwd_variables |> 
  purrr::map(setup_dwd_request_grid, years = 2008:2023, months = 1:12) |> 
  purrr::flatten() |> 
  purrr::map(~{
    file_name <- 
      glue::glue(
        "./data/dwd/{.x$indicator}_{.x$years}_{.x$months}.asc.gz"
      )
    
    dwd_location <-
      glue::glue(
        "https://opendata.dwd.de/climate_environment/CDC/grids_germany/",
        "monthly/{.x$indicator}/{.x$months_folder}/grids_germany_monthly_",
        "{.x$indicator}_{.x$years}{.x$months}.asc.gz"
      )
    
    if(.x$indicator == "air_temperature_mean") {
      dwd_location <-
        dwd_location |> 
        textworks::str_replace_nth(
          "air_temperature_mean", "air_temp_mean", 2  # Adjust path for specific variable
        )
    }
    
    dplyr::tibble(file_name, dwd_location)
  })

# Download data from C3S and save to the specified path
era5_requests |> 
  purrr::walk(~{
    ecmwfr::wf_request(
      user = user,          # API user ID
      request = .x,         # Request parameters
      transfer = FALSE,      # Enable data transfer
      path = "./data/era5/", # Destination folder for downloaded data
      verbose = FALSE       # Suppress detailed output
    )
  })

# Download DWD data and decompress
dwd_requests |> 
  purrr::walk(~{
    if(!file.exists(stringr::str_replace(.x$file_name, ".gz", ""))) {
      download.file(
        url = .x$dwd_location,
        destfile = .x$file_name,
        mode = "wb",
        quiet = TRUE
      )
      
      R.utils::gunzip(.x$file_name)  # Decompress the file
    }
  })

# Add wind speed to ERA5 data
era5_data$`10m_wind_speed` <-
  calculate_wind_speed(
    era5_data$`10m_u_component_of_wind`, 
    era5_data$`10m_v_component_of_wind`,
    "10m_wind_speed"  # Name for the wind speed variable
  )

# Update the list of ERA5 variables to include the calculated wind speed
era5_variables <- c(era5_variables, "10m_wind_speed")

# Process and load DWD data files
dwd_data <- 
  list.files("./data/dwd/", full.names = TRUE) |>          # Get list of all DWD files
  purrr::map(dwd_variables, stringr::str_subset, string = _) |>  # Filter files by variables
  purrr::map(terra::rast) |>                               # Load files as raster layers
  purrr::map(terra::app, mean) |>                          # Calculate the mean of each raster
  purrr::map(~{terra::crs(.x) <- "EPSG:31467"; .x}) |>     # Set CRS to EPSG:31467
  purrr::map(terra::project, y = "EPSG:4326") |>           # Reproject to WGS84 (EPSG:4326)
  purrr::imap(~{names(.x) <- dwd_variables[.y]; .x}) |>    # Assign names based on variables
  purrr::set_names(dwd_variables)                         # Assign names to the list

# Combine extracted ERA5 and DWD data with municipality shapefile
municipality_shape_era5_dwd <-
  dplyr::bind_cols(
    municipality_shape,  # Base shapefile with municipality geometries
    era5_data |> 
      purrr::map(
        exactextractr::exact_extract, y = municipality_shape, fun = "mean"  # Extract mean values
      ) |> 
      dplyr::bind_cols() |> 
      purrr::set_names(paste0("era5_", era5_variables)),  # Prefix variable names with "era5_"
    dwd_data |> 
      purrr::map(
        exactextractr::exact_extract, y = municipality_shape, fun = "mean"  # Extract mean values
      ) |> 
      dplyr::bind_cols() |> 
      purrr::set_names(paste0("dwd_", dwd_variables))  # Prefix variable names with "dwd_"
  )

# Normalize DWD variables for consistency
municipality_shape_era5_dwd <-
  municipality_shape_era5_dwd |> 
  dplyr::mutate(
    dwd_air_temperature_mean = (dwd_air_temperature_mean / 10) + 273.15,  # Convert to Kelvin
    dwd_precipitation = dwd_precipitation / 1000  # Convert precipitation from mm to meters
  )

# Save the final dataset enriched with weather variables
saveRDS(
  municipality_shape_era5_dwd, 
  "./data/era5/municipality_shape_era5_dwd.rds"  # Save as RDS file
)

# Create maps for all ERA5 and DWD variables
weather_maps <-
  c(paste0("era5_", era5_variables), paste0("dwd_", dwd_variables)) |>  # Combine all variables
  purrr::map(~{
    ggplot(municipality_shape_era5_dwd) +
      geom_sf(aes(fill = .data[[.x]]), color = NA) +  # Use variable as fill color
      scale_fill_viridis_c()                          # Apply viridis color scale
  }) |> 
  patchwork::wrap_plots(nrow = 3)  # Arrange all plots in a 3-row grid

# Save the combined maps as a high-resolution PNG image
ggplot2::ggsave(
  "./figures/municipalities_weather_maps.png",  # Output file path
  weather_maps,                                # Plot object
  dpi = 600,                                   # Set resolution to 600 DPI
  width = 15, height = 15                      # Set dimensions of the output image
)
