require 'erb'
require 'base64'
require 'open-uri'
require 'octokit'
require 'mail'

options = { :address   => ENV['SENDGRID_SERVER'],
            :port      => ENV['SENDGRID_PORT'],
            :domain    => ENV['SENDGRID_DOMAIN'],
            :user_name => ENV['SENDGRID_USERNAME'],
            :password  => ENV['SENDGRID_PASSWORD'],
          }

Mail.defaults do
  delivery_method :smtp, options
end

def sendmail(recipient, subject_line, text, html=nil)
  Mail.deliver do
    to      recipient
    from    "#{ENV['SENDGRID_FROM']} <#{ENV['SENDGRID_ADDRESS']}>"
    subject subject_line

    text_part do
        body text
    end

    if html
      html_part do
          content_type 'text/html; charset=UTF-8'
          body html
      end
    end
  end
end

def github_client(page_size = 100)
  @token = ENV['GITHUB_TOKEN'] || `git config --global github.token`.chomp

  if @token.empty?
    puts "You need to generate a GitHub token:"
    puts "\t * https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
    puts "\t * git config --global github.token <token>"
    puts
    puts "Export that as the `GITHUB_TOKEN` environment variable or put it in your ~/.gitconfig."
    exit 1
  end

  begin
    client = Octokit::Client.new(:access_token => @token, per_page: page_size)
  rescue => e
    puts "Github login error: #{e.message}"
    exit 1
  end

  client
end

task :default do
  puts 'This automates several github org housekeeping processes.'
  puts
  system("rake -T")
end

desc 'Generate and send a stale PR report with a sample of the oldest open PRs.'
task :stale_pulls do
  org    = 'puppetlabs'
  stale  = github_client.search_issues("is:pr state:open user:#{org} archived:false sort:created-asc")
  sample = stale[:items].sample(15)

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: stale pull requests',
    ERB.new(File.read('templates/stale_prs.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/stale_prs.html.erb'), nil, '-').result(binding),
  )
end

