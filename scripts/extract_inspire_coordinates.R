#' Extract INSPIRE Grid Coordinates
#'
#' This function extracts X and Y coordinates from INSPIRE grid cell IDs
#' for both 1km and 100m grid resolutions.
#'
#' @param inspire_ids A character vector of INSPIRE grid cell identifiers.
#' @return A tibble with extracted X and Y coordinates.
#' @import stringr
#' @import tibble
#' @export
extract_inspire_coordinates <- function (inspire_ids) {
  
  # Check if the first INSPIRE ID indicates a 1km grid resolution
  if (stringr::str_detect(inspire_ids[1], "1km")) {
    inspire_coordinates <-
      tibble::tibble(
        X =
          substr(inspire_ids, 10, 13) |>  # Extract X coordinate (4-digit grid reference)
          paste0("500") |>  # Append "500" to center the coordinate in the 1km grid
          as.numeric(),
        Y =
          substr(inspire_ids, 5, 8) |>  # Extract Y coordinate (4-digit grid reference)
          paste0("500") |>  # Append "500" to center the coordinate in the 1km grid
          as.numeric()
      )
  }
  
  # Check if the first INSPIRE ID indicates a 100m grid resolution
  if (stringr::str_detect(inspire_ids[1], "100m")) {
    inspire_coordinates <-
      tibble::tibble(
        X =
          substr(inspire_ids, 12, 16) |>  # Extract X coordinate (5-digit grid reference)
          paste0("50") |>  # Append "50" to center the coordinate in the 100m grid
          as.numeric(),
        Y =
          substr(inspire_ids, 6, 10) |>  # Extract Y coordinate (5-digit grid reference)
          paste0("50") |>  # Append "50" to center the coordinate in the 100m grid
          as.numeric()
      )
  }
  
  # Return the extracted coordinates
  inspire_coordinates
}