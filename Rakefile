require 'erb'
require 'base64'
require 'open-uri'
require 'octokit'
require 'net/smtp'

task :default do
  puts 'This rake task just grabs a sample of stale pull requests and sends out'
  puts 'an email report requesting they get some attention.'
  puts
  puts 'Simply run `rake stale_pulls` to start the mirror process.'
  puts
  system("rake -T")
end

desc 'Generate stale PR report'
task :stale_pulls do
  TOKEN = ENV['GITHUB_TOKEN'] || `git config --global github.token`.chomp

  if TOKEN.empty?
    puts "You need to generate a GitHub token:"
    puts "\t * https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
    puts "\t * git config --global github.token <token>"
    puts
    puts "Export that as the `GITHUB_TOKEN` environment variable or put it in your ~/.gitconfig."
    exit 1
  end

  begin
    client = Octokit::Client.new(:access_token => TOKEN, per_page: 100)
  rescue => e
    puts "Github login error: #{e.message}"
    exit 1
  end

  org    = 'puppetlabs'
  stale  = client.search_issues("is:pr state:open user:#{org} archived:false sort:created-asc")
  sample = stale[:items].sample(15)

  server    = ENV['SENDGRID_SERVER']
  address   = ENV['SENDGRID_ADDRESS']
  domain    = ENV['SENDGRID_DOMAIN']
  username  = ENV['SENDGRID_USERNAME']
  password  = ENV['SENDGRID_PASSWORD']
  email     = ENV['EMAIL_ADDRESS']

  message   = ERB.new(File.read('templates/stale_prs.erb')).result(binding)

  Net::SMTP.start(server, 2525, domain, username, password) do |smtp|
    smtp.send_message(message, address, email)
  end

end
