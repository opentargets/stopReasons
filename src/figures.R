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
lazyLoad(smart_load_name(dir, "predictions_by_therapy_summary"))

theme_set(theme_cowplot(font_size = 9))

p_predictions <- plot_grid(
     p_supertile,
     plot_grid(
         p_predictions_by_phase,
         p_byta_highlights,
         NULL,
         align = "v",
         rel_widths = c(0.425, 0.425, 0.15),
         labels = c("b", "c"),
         nrow = 1),
     nrow = 2,
     scale = 0.98,
     align = "v",
     axis = "r",
     rel_heights = c(1, 0.7),
     labels = c("a", NULL)
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
        base_width = 14
    )
})

####################
## Efficacy figure
####################

lazyLoad(smart_load_name(dir, "efficacy_main"))

theme_set(theme_cowplot(font_size = 9))

p_efficacy <- plot_grid(
    p_efficacy_main,
    p_animal_main,
    rel_widths = c(1, 0.8),
    nrow = 1,
    labels = c("a", "b")
)
p_efficacy


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
        base_height = 7,
        base_width = 13
    )
})

####################
## Safety figure
####################

lazyLoad(smart_load_name(dir, "safety_main"))

theme_set(theme_cowplot(font_size = 9))

p_safety <- p_safety_main

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
        base_height = 7,
        base_width = 9
    )
})


#####################################
## Supplementary figure: dendrogram
#####################################

lazyLoad(smart_load_name(dir, "simDendroPlot"))

theme_set(theme_cowplot(font_size = 9))

p_dend <- plot_grid(
    p_dendro,
    p_heatmap,
    p_categories,
    rel_widths = c(1, 0.2, 0.6),
    nrow = 1
)
p_dend

outputs <- c(
    "./docs/figures/figureDendro.png",
    "./docs/figures/figureDendro.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_dend,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 9,
        base_width = 7
    )
})


#####################################
## Supplementary figure: efficacy by stop reason
#####################################

lazyLoad(smart_load_name(dir, "efficacy_meta_stop_by_datatype_granular"))

theme_set(theme_cowplot(font_size = 9))

p_meta_stop_by_dt_granular

outputs <- c(
    "./docs/figures/efficacy_byStopReason.png",
    "./docs/figures/efficacy_byStopReason.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_meta_stop_by_dt_granular,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 11,
        base_width = 8
    )
})

#####################################
## Supplementary figure: efficacy by datatource
#####################################

lazyLoad(smart_load_name(dir, "efficacy_meta_by_genetic_ds"))

theme_set(theme_cowplot(font_size = 9))

p_efficacy_meta_by_genetic_ds

outputs <- c(
    "./docs/figures/efficacy_byGeneticDatasource.png",
    "./docs/figures/efficacy_byGeneticDatasource.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_efficacy_meta_by_genetic_ds,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 8,
        base_width = 12
    )
})

#####################################
## Supplementary figure: efficacy by L2G
#####################################

lazyLoad(smart_load_name(dir, "efficacy_gwasL2Gscore"))

theme_set(theme_cowplot(font_size = 9))

p_efficacy_gwas_l2g_score

outputs <- c(
    "./docs/figures/efficacy_l2g.png",
    "./docs/figures/efficacy_l2g.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_efficacy_gwas_l2g_score,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 6,
        base_width = 6
    )
})

#####################################
## Supplementary figure: somatic safety
#####################################

lazyLoad(smart_load_name(dir, "safety_by_cancer_datasource"))

theme_set(theme_cowplot(font_size = 9))

p_safety_by_cancer_datasource

outputs <- c(
    "./docs/figures/safety_somatic.png",
    "./docs/figures/safety_somatic.pdf"
)

lapply(outputs, function(x) {
    save_plot(
        filename = x,
        plot = p_safety_by_cancer_datasource,
        scale = 0.95,
        ncol = 1,
        nrow = 1,
        base_height = 6,
        base_width = 6
    )
})
