variable "bucket_name" {
  type = string
  description = "name of the bucket"
}

variable "packages" {
  type = list(string)
  description = "packages to upload"
}

variable "job_type" {
  type = string
  description = "job type"
}