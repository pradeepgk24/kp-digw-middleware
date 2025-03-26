resource "aws_s3_object" "_" {
  count = length(var.packages)
  bucket = var.bucket_name
  key    = format("%s/%s","data-integration-framework/libs/${var.job_type}-package", var.packages[count.index])
  source = "../../../${var.packages[count.index]}"
  etag = filemd5("../../../${var.packages[count.index]}")
}