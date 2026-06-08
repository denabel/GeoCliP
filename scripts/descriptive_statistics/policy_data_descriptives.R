################################################################################
### Policy data cleaning #######################################################
################################################################################


# Packages ----------------------------------------------------------------

library(tidyverse)
library(readxl)
library(sf)


# Load data ---------------------------------------------------------------

# Policy database
sequencing <- read_excel("./data/NKI/NKI_full_list_21022024.xlsx")


# Data cleaning -----------------------------------------------------------

# Policy database
# Drop irrelevant variables
sequencing <- sequencing |> 
  select(-c(Ressort, Referat, PT, `Arb.-Einh.`, `Ausführende Stelle`, 
            `Staat...11`, `Gemeindekennziffer...13`, `Stadt/Gemeinde...14`, 
            `Ort...15`, `Bundesland...16`, `Staat...17`, Verbundprojekt, 
            Förderart))

# Rename variables
sequencing <- sequencing |> 
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
sequencing <- sequencing |> 
  mutate(
    start_date = dmy(start_date),
    end_date = dmy(end_date)
  )

# Explore policy data -----------------------------------------------------

# Subset to end of 2023
sequencing <- sequencing |> 
  filter(ymd(start_date) <= "2023-12-31")

# How many municipalities participated in NKI until end of 2023?
length(unique(sequencing$municipality_code))

summary(sequencing$funding_sum)

ggplot(data = sequencing, mapping = aes(x=start_date)) +
  geom_histogram(binwidth=182)

options(scipen = 999)
funding_hist <- ggplot(data = sequencing, mapping = aes(x=funding_sum)) +
  geom_histogram(binwidth=1000)+
  theme_bw()+
  xlim(0,500000)+
  labs(title = "Distribution of funding amount by project", 
       subtitle = "X-scale cut-off at 500,000 Euro",
       x = "Amount of funding in Euro",
       y = "Count")

ggsave(funding_hist, filename = "./figures/funding_hist.png", dpi = 300,
       width = 5, height = 3, units = "in")

municipalities_count <- data.frame(table(sequencing$municipality_name))

ggplot(data = municipalities_count, mapping = aes(x=Freq)) +
  geom_histogram(binwidth=1)


funding_line <- data.frame(table(sequencing$funding_line))

sequencing |>
  filter(funding_line == "KSI - Modellprojekte zum Klimaschutz") |>
  ggplot(mapping = aes(x=start_date)) +
  geom_histogram(binwidth=1000)

table(sequencing$funding_line)

# Prepare NKI data
# We will generate quarterly period cumulative sums for funding sums

# Create the three-month period variable
sequencing <- sequencing |> 
  mutate(period = floor_date(start_date, "quarter"))

# Group by id and the new period variable, then sum "funding_sum"
quarters <- sequencing |> 
  group_by(municipality_code, period) |> 
  summarise(funding_quarter = sum(funding_sum, na.rm = TRUE),
            policy_activity = n())

summary(quarters$funding_quarter)

hist(log(quarters$funding_quarter+1))

# Now we can merge this with a full dataset for all municipalities and quarters
# 2008 - 2023

# Municipalities shapefiles
municipalities <- st_read("./data/gemeinden_utm32/vg250_ebenen_0101/VG250_GEM.shp") |> 
  select(AGS, GEN, BEZ, geometry)

# There are duplicates in the dataframe - easy fix is to exclude it for now but
# need to check more thoroughly (probably because of multiple polygons and I
# need a proper strategy for that)
municipalities <- municipalities |> 
  distinct(AGS, .keep_all=TRUE)

# Create a template dataframe with all id and quarterly intervals from 2008 to 2023
data <- expand.grid(
  id = unique(municipalities$AGS),
  quarter_year = seq(as.Date("2008-01-01"), as.Date("2023-12-31"), by = "3 months")
)

# Merge with NKI data
data <- data |> 
  left_join(quarters, by = c("id" = "municipality_code",
                             "quarter_year" = "period"))

sum(is.na(data$funding_quarter))
# Roughly 200 observations from the NKI database were not merged - these
# are presumably the observations from 2024

# Transform NAs to 0
data <- data |> 
  mutate(funding_quarter = case_when(
    is.na(funding_quarter) ~ 0,
    TRUE ~ funding_quarter
  ),
  policy_activity = case_when(
    is.na(policy_activity) ~ 0,
    TRUE ~ policy_activity)
  )

# Also generate a cumulative sum variable over id and quarters
data <- data |> 
  arrange(id, quarter_year) |> 
  group_by(id) |> 
  mutate(cumulative_funding = cumsum(funding_quarter),
         cumulative_activity = cumsum(policy_activity)) |> 
  mutate(log_cum_fund = log(cumulative_funding + 1)) |> 
  ungroup()

# Filter all observations which are not part of the NKI until end of 2023
data <- data |> 
  group_by(id) |> 
  filter(any(cumulative_activity > 0 & ymd(quarter_year) == "2023-10-01")) |> 
  ungroup()

# Subset NKI data to Bonn
bonn <- sequencing |> 
  filter(municipality_code == "05314000")

# Visualize sequences over time
NKI_over_time <- ggplot(data, aes(x = quarter_year, y = cumulative_activity, group = factor(id))) +
  geom_line(color = "darkgrey", size = 0.5, alpha=0.2) +
  geom_line(data = subset(data, id == "05314000"),
            aes(x = quarter_year, y = cumulative_activity),
            color = "#005a32", size = 1.2) +
  # geom_vline(xintercept = as.Date(c("2009-10-01", "2013-07-01", 
  #                                   "2019-10-01", "2022-10-01")), 
  #            linetype="dashed", 
  #            color = "#005a32", size=1)+
  # annotate("text", 
  #          x = as.Date("2009-10-01"), 
  #          y = max(data$cumulative_activity) - 50, 
  #          label = "Climate strategy", color = "#005a32", 
  #          angle = 90, vjust = -1) +
  # annotate("text", 
  #          x = as.Date("2013-07-01"), 
  #          y = max(data$cumulative_activity) - 50, 
  #          label = "Lighting refurbishment", color = "#005a32", 
  #          angle = 90, vjust = -1) +
  # annotate("text", 
  #          x = as.Date("2019-10-01"), 
  #          y = max(data$cumulative_activity) - 50, 
  #          label = "Refurbishment public pools", color = "#005a32", 
  #          angle = 90, vjust = -1) +
  # annotate("text", 
  #          x = as.Date("2022-10-01"), 
  #          y = max(data$cumulative_activity) - 50, 
  #          label = "Bicycle parking", color = "#005a32", 
  #          angle = 90, vjust = -1) +
  geom_vline(xintercept = as.Date(c("2019-07-04")),
             linetype="dashed",
             color = "red", size=1)+
  annotate("text",
           x = as.Date("2019-07-04"),
           y = max(data$cumulative_activity) - 50,
           label = "Climate emergency", color = "red",
           angle = 90, vjust = -1) +
  labs(x = "Year", y = "Count",
       title = "NKI Policy Activity between 2008 and 2023",
       subtitle = "City of Bonn and selected projects highlighted in green") +
  theme_minimal()

ggsave(NKI_over_time, filename = "./figures/NKI_over_time.png", dpi = 300,
       width = 5, height = 4, units = "in", background ="white")