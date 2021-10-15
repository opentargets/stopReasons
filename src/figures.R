library(tidyverse)
library(cowplot)
library(stringr)
library(viridis)

dir <- normalizePath("./temp/")
# Function to quickly load chunks based on name
smart_load_name <- function(dir, key) {
  allfiles <- list.files(dir, pattern = ".RData")
  allfiles <- allfiles[stringr::str_detect(allfiles, key)]
  allfiles <- allfiles[which.min(stringr::str_length(allfiles))]
  filename <- stringr::str_match(allfiles, "(.+)\\.RData")[, 2]
  return(paste(dir, filename, sep = "/"))
}
scientific_10 <- function(x) {
  parse(text = gsub("e", " %*% 10^", scales::scientific_format()(x)))
}

######################
## Predictions figure
######################

lazyLoad(smart_load_name(dir, "predictions_by_date"))
lazyLoad(smart_load_name(dir, "predictions_by_phase"))

theme_set(theme_cowplot(font_size = 9))

p_predictions <- plot_grid(
    p_predictions_by_date,
    p_predictions_by_phase,
    nrow = 2,
    scale = 0.98,
    align = "v",
    axis = "r",
    rel_heights = c(1, 1),
    labels = c("a", "b")
)

outputs <- c(
    "./docs/figures/figurePredictions.png",
    "./docs/figures/figurePredictions.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_predictions,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 9,
        base_width = 9
    )
})

####################
## Efficacy figure
####################

lazyLoad(smart_load_name(dir, "efficacy_meta_stop_by_datatype"))
lazyLoad(smart_load_name(dir, "efficacy_gwasL2Gscore"))

theme_set(theme_cowplot(font_size = 9))

p_efficacy <- plot_grid(
    p_meta_stop_by_datatype,
    p_efficacy_gwas_l2g_score,
    nrow = 2,
    scale = 0.98,
    align = "v",
    axis = "l",
    rel_heights = c(1, 0.6),
    labels = c("a", "b")
)

outputs <- c(
    "./docs/figures/figureEfficacy.png",
    "./docs/figures/figureEfficacy.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_efficacy,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 9,
        base_width = 6
    )
})

####################
## Safety figure
####################

lazyLoad(smart_load_name(dir, "safety_byTA"))
lazyLoad(smart_load_name(dir, "safety_by_genetic_constrain"))

theme_set(theme_cowplot(font_size = 9))

p_safety <- plot_grid(
    p_safety_by_tA,
    p_safety_by_genetic_constrain,
    nrow = 2,
    scale = 0.98,
    align = "v",
    axis = "l",
    rel_heights = c(1, 0.6),
    labels = c("a", "b")
)

outputs <- c(
    "./docs/figures/figureSafety.png",
    "./docs/figures/figureSafety.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_safety,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 9,
        base_width = 6
    )
})