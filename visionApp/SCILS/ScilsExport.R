## ---- include = FALSE---------------------------------------------------------
knitr::opts_chunk$set(
  collapse = TRUE,
  comment = "#>",
  error = FALSE
)

# scils_file_path <- "C:\\Users\\UF biochemistry\\UK-Metabolomics Dropbox\\Ramon sun\\In-House MALDI Files\\04292024_tara_5xWT_old\\05012024_glygly_fullset.slx"
# save_path <- "C:\\Users\\UF biochemistry\\UK-Metabolomics Dropbox\\Ramon sun\\In-House MALDI Files\\04292024_tara_5xWT_old\\exports\\csv\\pbp\\pbp_gly_no_norm_test07252024.csv"
# peaklist_name <- "glycans_rr"



tryCatch( {

sink(file = r_output_filename, append = FALSE)
## ----setup--------------------------------------------------------------------
library(SCiLSLabClient)


## -----------------------------------------------------------------------------
# The filename variable holds the path to the *.slx file.
# Replace accordingly for your own dataset.
filename <- scils_file_path
example_data <- SCiLSLabOpenLocalSession(filename, timeout = 60)

# Sys.setenv("SCILSMSSERVER_LICENSE" = "130-2448274819-17")


## -----------------------------------------------------------------------------

getAttributeDF <- function(regionTree, duplicateValue = NA){
  
  if(!"RegionTree" %in% class(regionTree)){
    stop("RegionTree argument is not of class 'RegionTree'")
  }
  
  # Assemble the attributes:
  # The attributes will be represented as a tree of environments, with one
  # environment that holds an environment for each attribute, that holds a slot
  # for each level with the spots.
  allRegions <- flattenRegionTree(regionTree)
  attributes <- new.env()
  for (region in allRegions){
    for (att in 1:nrow(region$attributes)) {
      attribute_name <- region$attributes[att, ]$name
      attribute_level <- region$attributes[att, ]$value
      if (!attribute_name %in% names(attributes)) {
        attributes[[attribute_name]] <- new.env()
      }
      
      if (!attribute_level %in% names(attributes[[attribute_name]])) {
        attributes[[attribute_name]][[attribute_level]] <-
          region$spots$spotId
      } else{
        attributes[[attribute_name]][[attribute_level]] <- union(
          attributes[[attribute_name]][[attribute_level]],
          region$spots$spotId)
      }
    }
  }
  

  # Create a return data.frame with all spots
  return_df <- allRegions[[1]]$spots
  
  for( attribute_name in names(attributes)){
    attr <- attributes[[attribute_name]]
    
    # Create a temporary data.frame with the spot ids and attribute level for each
    # attribute
    tmp <- do.call(rbind.data.frame, lapply(names(attr), function (x){
      data.frame(attr[[x]], x )
    }))
    names(tmp) <- c("spotId", attribute_name)
    
    # detect and indicate duplicated spots
    duplicates <- duplicated(tmp$spotId) | duplicated(tmp$spotId, fromLast = TRUE)
    tmp[duplicates, 2] <- duplicateValue
    
    # detect and indicate duplicated spots
    tmp <- unique(tmp)
    
    # merge the temporary data.frame with the return data.frame on the first
    # columns
    return_df <- merge(return_df, tmp, by.x = 1, by.y = 1, all.x = TRUE)
  }
  
  return_df
}


## -----------------------------------------------------------------------------
regionTree <- getRegionTree(example_data)
attribute_df <- getAttributeDF(regionTree)
str(attribute_df)


## -----------------------------------------------------------------------------
str(getAttributeDF(regionTree, duplicateValue = "#!duplicated") )


## -----------------------------------------------------------------------------
# Retrieve the peak list for "All Features"
# Without specifying an id or name in 'getFeatures' the "All Features"
# feature list is retrieved
all_features <- getFeatures(example_data, mode = 'area', name = peaklist_name)
head(all_features)


## -----------------------------------------------------------------------------
all_features <- all_features[all_features$hasData, ]


## -----------------------------------------------------------------------------
# get the normalization ID for the normalization "Total Ion Count"
#normalizations <- getNormalizations(example_data)
#ticNorm <- normalizations$uniqueId[normalizations$description == "Total Ion Count"]

#get the peak intensity matrix by applying getFeatureIntensities to all
# feature id's in the feature list.
intensityMatrix <- do.call(
  cbind,
  lapply(all_features$id,
         function(x) getFeatureIntensities(
           example_data,
           x,
           mode = 'area',
           regionId = 'Regions',
           normId = "")$intensity
  )
)
# assign the column names of the intensity matrix as the mean m/z value of
# the m/z interval
colnames(intensityMatrix) <- makeFeatureNames(all_features)



## -----------------------------------------------------------------------------
spot_ids <- getRegionSpots(example_data)$spotId
intensityDF <- data.frame( spotId = spot_ids, intensityMatrix)

all_data_df <- merge(attribute_df, intensityDF, all.x = TRUE)

#Showing the first five rows and 15 columns of the resulting intensity data.frame
#all_data_df[1:5,1:15]

write.csv(all_data_df, save_path)
## -----------------------------------------------------------------------------
str(close(example_data))

sink(file = NULL)

} , error = function(e) {

  print(e$message)
  sink(file = NULL)
}


)

